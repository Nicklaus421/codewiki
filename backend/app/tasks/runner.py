"""异步任务调度：进程内 asyncio 队列，执行 clone → 分析 → 生成 Wiki 文档。

生产扩展：可将任务体替换为 Redis + RQ / Celery 队列（见 docs/DESIGN.md）。
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select, text

from ..config import get_settings
from ..db import get_session_maker
from ..models import DocTask, Repository, WikiPage
from ..services import git_service
from ..services.analyzer import analyze_repo
from ..services.generator import Generator

logger = logging.getLogger(__name__)

# task_id -> asyncio.Task，用于取消
_jobs: dict[str, asyncio.Task] = {}


# ---------- 工具 ----------
async def _new_task(repo_id: str, kind: str) -> str:
    import uuid

    task_id = uuid.uuid4().hex
    maker = get_session_maker()
    async with maker() as session:
        session.add(DocTask(id=task_id, repo_id=repo_id, kind=kind, status="pending"))
        await session.commit()
    return task_id


async def _update_task(task_id: str, status: str | None = None, step: str | None = None,
                       progress: int | None = None, message: str | None = None) -> None:
    maker = get_session_maker()
    async with maker() as session:
        task = await session.get(DocTask, task_id)
        if task is None:
            return
        if status is not None:
            task.status = status
        if step is not None:
            task.step = step
        if progress is not None:
            task.progress = progress
        if message is not None:
            task.message = message
        await session.commit()


async def _update_repo(repo_id: str, status: str | None = None, **fields) -> None:
    maker = get_session_maker()
    async with maker() as session:
        repo = await session.get(Repository, repo_id)
        if repo is None:
            return
        if status is not None:
            repo.status = status
        for k, v in fields.items():
            if hasattr(repo, k):
                setattr(repo, k, v)
        await session.commit()


async def _clear_pages(repo_id: str) -> None:
    maker = get_session_maker()
    async with maker() as session:
        async with session.begin():
            await session.execute(delete(WikiPage).where(WikiPage.repo_id == repo_id))


async def _save_pages(repo_id: str, drafts, stats: dict) -> None:
    maker = get_session_maker()
    async with maker() as session:
        async with session.begin():
            await session.execute(delete(WikiPage).where(WikiPage.repo_id == repo_id))
            for d in drafts:
                session.add(
                    WikiPage(
                        repo_id=repo_id, path=d.path, title=d.title, page_type=d.page_type,
                        source=d.source, content=d.content, source_files=d.source_files,
                        order=d.order,
                    )
                )
            repo = await session.get(Repository, repo_id)
            if repo is None:
                raise RuntimeError("仓库已被删除")
            repo.status = "ready"
            repo.error = ""
            stats["generated_at"] = datetime.now(timezone.utc).isoformat()
            stats["page_count"] = len(drafts)
            repo.stats = stats
            # 重建全文索引（external content 表）
            await session.execute(
                text("INSERT INTO wiki_pages_fts(wiki_pages_fts) VALUES('rebuild')")
            )


# ---------- 任务执行 ----------
async def submit_repo_job(repo_id: str, url: str, branch: str, kind: str = "add") -> str:
    """创建任务并调度执行，返回 task_id。"""
    task_id = await _new_task(repo_id, kind)
    _jobs[task_id] = asyncio.create_task(
        _run_job(task_id, repo_id, url, branch, kind),
        name=f"repo-job-{repo_id}",
    )
    return task_id


def cancel_jobs_for_repo(repo_id: str) -> None:
    for task_id, task in list(_jobs.items()):
        if task.get_name() == f"repo-job-{repo_id}":
            task.cancel()
            _jobs.pop(task_id, None)


async def _run_job(task_id: str, repo_id: str, url: str, branch: str, kind: str) -> None:
    settings = get_settings()
    try:
        # 1. 克隆
        await _update_task(task_id, status="running", step="cloning", progress=5, message="正在克隆代码仓库...")
        await _update_repo(repo_id, status="cloning")
        source_dir = await git_service.clone_repo(repo_id, url, branch)
        size = await git_service.get_repo_size(source_dir)
        max_bytes = settings.max_repo_size_mb * 1024 * 1024
        if size > max_bytes:
            raise RuntimeError(f"仓库超过大小上限 {settings.max_repo_size_mb}MB（实际 {size // 1024 // 1024}MB）")

        default_branch = await git_service.detect_default_branch(source_dir)
        branch_used = branch or default_branch
        await _update_task(task_id, step="analyzing", progress=20, message="正在分析代码仓库结构...")
        await _update_repo(
            repo_id,
            status="analyzing",
            default_branch=default_branch,
            branch=branch_used,
            source_path=str(source_dir),
        )

        # 2. 分析
        analysis = await asyncio.to_thread(analyze_repo, repo_id, source_dir)
        await _update_repo(
            repo_id,
            status="generating",
            language_stats=analysis.language_stats,
            stats=analysis.stats,
        )

        # 3. 生成文档
        await _update_task(task_id, step="generating", progress=30, message="正在生成 Wiki 文档...")

        async def progress_cb(i: int, total: int, path: str) -> None:
            pct = 30 + int(65 * (i + 1) / max(total, 1))
            await _update_task(task_id, step="generating", progress=min(pct, 95),
                               message=f"正在生成 {path}（{i + 1}/{total}）")

        generator = Generator(analysis)
        drafts = await generator.generate(progress_cb)

        # 4. 持久化
        await _save_pages(repo_id, drafts, analysis.stats)
        await _update_task(task_id, status="done", step="done", progress=100,
                           message=f"文档生成完成，共 {len(drafts)} 个页面（"
                                   f"{sum(1 for d in drafts if d.source == 'ai')} AI / "
                                   f"{sum(1 for d in drafts if d.source == 'static')} 静态）")
        logger.info("仓库 %s 文档生成完成", repo_id)
    except asyncio.CancelledError:
        logger.info("任务 %s 被取消", task_id)
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("仓库 %s 处理失败", repo_id)
        await _update_repo(repo_id, status="failed", error=str(e)[:2000])
        await _update_task(task_id, status="failed", step="failed", progress=100,
                           message=f"处理失败：{e}")
    finally:
        _jobs.pop(task_id, None)

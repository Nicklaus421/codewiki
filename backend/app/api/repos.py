"""代码仓资产：添加 / 列表 / 详情 / 删除 / 重新生成。"""
import logging
import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..models import DocTask, Repository, WikiPage
from ..schemas import FileEntry, RepoAddResponse, RepoCreate, RepoDetail, RepoListItem
from ..services import git_service
from ..tasks import runner
from .files import dir_entries

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=RepoAddResponse, status_code=202)
async def create_repo(body: RepoCreate, session: AsyncSession = Depends(get_session)):
    url = body.url.strip()
    if not git_service.is_valid_git_url(url):
        raise HTTPException(status_code=422, detail="无效的 git 仓库地址")
    branch = git_service.sanitize_branch(body.branch or "")

    dup = (
        await session.execute(select(Repository).where(Repository.url == url))
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail=f"仓库已存在：{dup.name}")

    name = (body.name or git_service.repo_name_from_url(url)).strip() or "unnamed-repo"
    repo = Repository(name=name, url=url, branch=branch)
    session.add(repo)
    await session.commit()
    await session.refresh(repo)

    task_id = await runner.submit_repo_job(repo.id, url, branch, kind="add")
    logger.info("新增仓库 %s (%s)，任务 %s", name, url, task_id)
    return RepoAddResponse(id=repo.id, task_id=task_id, status="pending")


@router.get("", response_model=list[RepoListItem])
async def list_repos(session: AsyncSession = Depends(get_session)):
    counts = (
        select(WikiPage.repo_id, func.count(WikiPage.id).label("cnt"))
        .group_by(WikiPage.repo_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(Repository, func.coalesce(counts.c.cnt, 0).label("cnt"))
            .outerjoin(counts, counts.c.repo_id == Repository.id)
            .order_by(Repository.created_at.desc())
        )
    ).all()
    return [
        RepoListItem(
            id=r.id, name=r.name, url=r.url, branch=r.branch, default_branch=r.default_branch,
            status=r.status, error=r.error, language_stats=r.language_stats or {},
            stats=r.stats or {}, page_count=cnt, created_at=r.created_at, updated_at=r.updated_at,
        )
        for r, cnt in rows
    ]


@router.get("/{repo_id}", response_model=RepoDetail)
async def get_repo(repo_id: str, session: AsyncSession = Depends(get_session)):
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    page_count = (
        await session.execute(
            select(func.count(WikiPage.id)).where(WikiPage.repo_id == repo_id)
        )
    ).scalar() or 0
    top_tree: list[FileEntry] = []
    if repo.source_path:
        try:
            top_tree = dir_entries(repo_id, "")
        except HTTPException:
            top_tree = []
    return RepoDetail(
        id=repo.id, name=repo.name, url=repo.url, branch=repo.branch,
        default_branch=repo.default_branch, status=repo.status, error=repo.error,
        language_stats=repo.language_stats or {}, stats=repo.stats or {},
        page_count=page_count, created_at=repo.created_at, updated_at=repo.updated_at,
        top_tree=top_tree,
    )


@router.delete("/{repo_id}", status_code=204)
async def delete_repo(repo_id: str, session: AsyncSession = Depends(get_session)):
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    runner.cancel_jobs_for_repo(repo_id)
    source_dir = get_settings().repo_source_dir(repo_id)
    if source_dir.exists():
        shutil.rmtree(source_dir, ignore_errors=True)
    await session.delete(repo)
    await session.commit()
    logger.info("删除仓库 %s", repo_id)


@router.post("/{repo_id}/regenerate", response_model=RepoAddResponse, status_code=202)
async def regenerate_repo(repo_id: str, session: AsyncSession = Depends(get_session)):
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    runner.cancel_jobs_for_repo(repo_id)
    task_id = await runner.submit_repo_job(repo.id, repo.url, repo.branch, kind="regenerate")
    return RepoAddResponse(id=repo.id, task_id=task_id, status="pending")

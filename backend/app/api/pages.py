"""Wiki 页面：列表与内容。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Repository, WikiPage
from ..schemas import PageContent, PageSummary
from ..services.analyzer import read_source_text
from ..services.storage import PathError, resolve_source_path

router = APIRouter()


@router.get("/{repo_id}/pages", response_model=list[PageSummary])
async def list_pages(repo_id: str, session: AsyncSession = Depends(get_session)):
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    rows = (
        await session.execute(
            select(WikiPage)
            .where(WikiPage.repo_id == repo_id)
            .order_by(WikiPage.order, WikiPage.path)
        )
    ).scalars().all()
    return [
        PageSummary(
            id=r.id, path=r.path, title=r.title, page_type=r.page_type,
            source=r.source, order=r.order, updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/{repo_id}/pages/{page_path:path}", response_model=PageContent)
async def get_page(repo_id: str, page_path: str, session: AsyncSession = Depends(get_session)):
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    row = (
        await session.execute(
            select(WikiPage).where(
                WikiPage.repo_id == repo_id, WikiPage.path == page_path
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        return PageContent(
            id=row.id, path=row.path, title=row.title, page_type=row.page_type,
            source=row.source, order=row.order, updated_at=row.updated_at,
            content=row.content, source_files=row.source_files or [],
        )
    # wiki 页不存在时，回退渲染源码中的 Markdown 文档
    md = _md_page(repo, page_path)
    if md is not None:
        return md
    raise HTTPException(status_code=404, detail="页面不存在")


def _md_page(repo: Repository, page_path: str) -> PageContent | None:
    """将源码中的 .md 文档作为页面返回；非 md 文件返回 None。"""
    cands = [page_path]
    if not page_path.lower().endswith(".md"):
        cands.append(page_path + ".md")
    for cand in cands:
        if not cand or cand.startswith("/") or ".." in cand.split("/"):
            continue
        try:
            p = resolve_source_path(repo.id, cand.strip("/"))
        except PathError:
            continue
        if not p.is_file() or not p.name.lower().endswith(".md"):
            continue
        return PageContent(
            id=0, path=cand.strip("/"), title=p.stem,
            page_type="md", source="md", order=0, updated_at=repo.updated_at,
            content=read_source_text(p, 300_000), source_files=[],
        )
    return None

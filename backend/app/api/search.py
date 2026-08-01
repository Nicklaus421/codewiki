"""全文搜索：优先 FTS5(trigram)，短查询/空结果回退 LIKE。"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import WikiPage
from ..schemas import SearchHit, SearchResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_SNIPPET_LEN = 220


def _make_snippet(content: str, q: str) -> str:
    idx = content.lower().find(q.lower())
    if idx == -1:
        return content[:_SNIPPET_LEN] + ("…" if len(content) > _SNIPPET_LEN else "")
    start = max(0, idx - 60)
    end = min(len(content), idx + len(q) + 140)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return prefix + content[start:end].replace("\n", " ").strip() + suffix


async def _fts_search(session: AsyncSession, q: str, repo_id: str | None) -> list[SearchHit]:
    esc = q.replace('"', '""')
    match = f'"{esc}"'
    stmt = text(
        """
        SELECT wp.repo_id, r.name AS repo_name, wp.path, wp.title, wp.content
        FROM wiki_pages_fts fts
        JOIN wiki_pages wp ON wp.id = fts.rowid
        JOIN repositories r ON r.id = wp.repo_id
        WHERE wiki_pages_fts MATCH :m
          AND (:rid IS NULL OR wp.repo_id = :rid)
        ORDER BY rank
        LIMIT 50
        """
    )
    rows = await session.execute(stmt, {"m": match, "rid": repo_id})
    hits: list[SearchHit] = []
    for r in rows:
        hits.append(
            SearchHit(
                repo_id=r.repo_id, repo_name=r.repo_name, path=r.path, title=r.title,
                snippet=_make_snippet(r.content, q),
            )
        )
    return hits


async def _like_search(session: AsyncSession, q: str, repo_id: str | None) -> list[SearchHit]:
    stmt = select(WikiPage).where(
        WikiPage.content.contains(q) | WikiPage.title.contains(q)
    )
    if repo_id:
        stmt = stmt.where(WikiPage.repo_id == repo_id)
    stmt = stmt.limit(50)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        SearchHit(
            repo_id=r.repo_id, repo_name="", path=r.path, title=r.title,
            snippet=_make_snippet(r.content, q),
        )
        for r in rows
    ]


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    repo_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    q = q.strip()
    if not q:
        return SearchResponse(query=q, hits=[])
    try:
        hits = await _fts_search(session, q, repo_id)
    except Exception as exc:  # noqa: BLE001  FTS 语法等异常回退
        logger.warning("FTS 搜索失败，回退 LIKE：%s", exc)
        hits = []
    if not hits:
        hits = await _like_search(session, q, repo_id)
    return SearchResponse(query=q, hits=hits)

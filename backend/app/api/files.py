"""源码文件浏览：目录树（懒加载）与文件内容。"""
import os
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Repository
from ..schemas import FileEntry
from ..services import analyzer
from ..services.storage import PathError, resolve_source_path

router = APIRouter()

MAX_FILE_READ_CHARS = 300_000  # 单文件最多返回字符数

_HIDE_DOT = True  # 浏览时隐藏隐藏文件/目录


@lru_cache(maxsize=4096)
def _dir_has_md(dir_path: str) -> bool:
    """判断目录内（递归）是否存在 Markdown 文档，用于 md 树剪枝空目录。"""
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                if entry.name in analyzer.SKIP_DIRS:
                    continue
                if entry.is_dir():
                    if _dir_has_md(entry.path):
                        return True
                elif entry.name.lower().endswith(".md"):
                    return True
    except OSError:
        return False
    return False


def dir_entries(repo_id: str, rel: str) -> list[FileEntry]:
    """列出目录下的条目（顶层已含 git 克隆后的常规目录）。"""
    root = resolve_source_path(repo_id, rel)
    if not root.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")
    entries: list[FileEntry] = []
    try:
        items = sorted(os.scandir(root), key=lambda e: (e.is_file(), e.name.lower()))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"读取目录失败：{exc}") from exc
    for entry in items:
        name = entry.name
        if name in analyzer.SKIP_DIRS or name in analyzer.SKIP_FILES:
            continue
        if _HIDE_DOT and name.startswith("."):
            continue
        rel_path = f"{rel}/{name}" if rel else name
        try:
            size = entry.stat(follow_symlinks=False).st_size if entry.is_file() else 0
        except OSError:
            size = 0
        if entry.is_dir():
            entries.append(FileEntry(name=name, path=rel_path, type="dir"))
        else:
            dot = name.rfind(".")
            if dot >= 0 and name[dot:].lower() in analyzer.SKIP_EXTS:
                continue
            entries.append(FileEntry(name=name, path=rel_path, type="file", size=size))
    return entries


@router.get("/{repo_id}/tree")
async def get_tree(repo_id: str, path: str = "", only_md: bool = False):
    """返回某目录下的条目（懒加载）。only_md=true 时只返回 Markdown 文档与其所在目录。"""
    try:
        entries = dir_entries(repo_id, path.strip("/"))
    except HTTPException:
        raise
    if only_md:
        entries = _filter_md(entries, repo_id)
    return {"path": path.strip("/"), "entries": [e.model_dump() for e in entries]}


def _filter_md(entries: list[FileEntry], repo_id: str) -> list[FileEntry]:
    """保留 .md 文件与递归包含 .md 文件的目录（剪枝空目录）。"""
    out: list[FileEntry] = []
    for e in entries:
        if e.type == "file":
            if e.name.lower().endswith(".md"):
                out.append(e)
        else:
            try:
                dir_path = str(resolve_source_path(repo_id, e.path))
            except PathError:
                continue
            if _dir_has_md(dir_path):
                out.append(e)
    return out


@router.get("/{repo_id}/file")
async def get_file(repo_id: str, path: str, session: AsyncSession = Depends(get_session)):
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    if not path or path.startswith("/") or ".." in path.split("/"):
        raise HTTPException(status_code=400, detail="非法路径")
    try:
        p = resolve_source_path(repo_id, path.strip("/"))
    except PathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not p.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    if p.stat().st_size > MAX_FILE_READ_CHARS:
        content = analyzer.read_source_text(p, MAX_FILE_READ_CHARS) + "\n...(文件过大，已截断)"
    else:
        content = analyzer.read_source_text(p, MAX_FILE_READ_CHARS)
    return {
        "path": path.strip("/"),
        "name": p.name,
        "language": analyzer._lang_of(p.name),
        "size": p.stat().st_size,
        "content": content,
    }

"""源码文件安全读写：防止路径穿越。"""
from pathlib import Path

from ..config import get_settings


class PathError(ValueError):
    pass


def resolve_source_path(repo_id: str, rel: str) -> Path:
    """将相对路径解析为仓库源码目录下的绝对路径，杜绝 ../ 穿越。"""
    root = get_settings().repo_source_dir(repo_id).resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root):
        raise PathError("非法路径访问")
    return p

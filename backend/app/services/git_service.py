"""Git 相关操作：URL 校验、浅克隆、默认分支探测、仓库大小。"""
import asyncio
import logging
import re
from pathlib import Path

from ..config import get_settings

logger = logging.getLogger(__name__)

GIT_URL_RE = re.compile(
    r"^(?:https?://|git@|ssh://|git://)[\w.-]+(?:/|:)[\w./@~:-]+$", re.IGNORECASE
)
# git 引用名非法字符黑名单：分支名允许中文等任意 UTF-8，仅拒绝 git 本身禁止的字符/结构
_BRANCH_INVALID = re.compile(r"[~\s\^:?*\[\]\\]|\.\.|@{|^-|[/.]$")


class GitError(RuntimeError):
    pass


def is_valid_git_url(url: str) -> bool:
    return bool(GIT_URL_RE.match(url.strip()))


def repo_name_from_url(url: str) -> str:
    """从 URL 推导仓库名，如 git@github.com:org/repo.git -> repo。"""
    u = url.strip().rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    name = u.rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return name or "unnamed-repo"


def sanitize_branch(branch: str) -> str:
    branch = branch.strip()
    if not branch or len(branch) > 200:
        return ""
    if _BRANCH_INVALID.search(branch):
        return ""
    return branch


async def _run_git(args: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[str, str]:
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise GitError(f"git 命令超时（{timeout}s）：{' '.join(args[:3])} ...")
    if proc.returncode != 0:
        raise GitError((stderr or b"").decode(errors="replace").strip() or f"git {' '.join(args)} 失败")
    return stdout.decode(errors="replace").strip(), stderr.decode(errors="replace").strip()


async def clone_repo(repo_id: str, url: str, branch: str) -> Path:
    """浅克隆（--depth 1 --single-branch），返回源码目录路径。"""
    settings = get_settings()
    dest = settings.repo_source_dir(repo_id)
    if dest.exists():
        logger.info("目录已存在，先清空再克隆：%s", dest)
        await asyncio.to_thread(_rmtree, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    args = ["clone", "--depth", "1", "--single-branch", "--no-tags"]
    if branch:
        args += ["--branch", branch]
    args += [url, str(dest)]
    logger.info("开始克隆 %s -> %s（branch=%s）", url, dest, branch or "default")
    await _run_git(args, timeout=settings.clone_timeout)
    return dest


async def detect_default_branch(source_dir: Path) -> str:
    """从 origin/HEAD 探测默认分支名。"""
    try:
        out, _ = await _run_git(["-C", str(source_dir), "branch", "-r"], timeout=30)
    except GitError:
        return "main"
    target = None
    for line in out.splitlines():
        if "HEAD" in line:
            target = line.split("->", 1)[-1].strip()
            break
    if target:
        return target.split("/", 1)[-1]
    for cand in ("origin/main", "origin/master", "origin/develop"):
        if cand in out:
            return cand.split("/", 1)[-1]
    return "main"


async def get_repo_size(source_dir: Path) -> int:
    """返回仓库总大小（字节）。"""
    total = 0
    for p in source_dir.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def _rmtree(path: Path) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)

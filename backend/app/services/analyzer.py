"""代码仓分析：文件树、语言统计、关键文件识别、README 提取、模块目录识别。"""
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# 跳过目录 / 文件：避免噪音与二进制
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build",
    ".next", ".nuxt", ".cache", "target", "vendor", ".tox", ".pytest_cache",
    ".gradle", ".idea", ".vscode", "coverage", ".mypy_cache", ".ruff_cache",
    ".gitmodules", ".hg", ".svn", "site-packages", ".terraform", ".serverless",
}
SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp", ".webp", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".whl", ".tgz", ".xz",
    ".so", ".dylib", ".a", ".o", ".obj", ".exe", ".dll", ".class", ".jar", ".pyc",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav", ".flac", ".bin", ".db", ".sqlite",
    ".lock", ".map", ".min.js", ".min.css", ".wasm", ".parquet", ".csv", ".xlsx", ".xls",
}
SKIP_FILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "Pipfile.lock"}

# 扩展名 -> 语言
EXT_LANG = {
    ".py": "Python", ".pyi": "Python", ".js": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".jsx": "JavaScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".c": "C", ".h": "C", ".cpp": "C++", ".hpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".cs": "C#", ".php": "PHP", ".rb": "Ruby", ".swift": "Swift", ".sh": "Shell",
    ".bash": "Shell", ".zsh": "Shell", ".fish": "Shell", ".ps1": "PowerShell",
    ".sql": "SQL", ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".sass": "Sass", ".less": "LESS", ".vue": "Vue", ".svelte": "Svelte",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".ini": "INI",
    ".conf": "Config", ".xml": "XML", ".proto": "Protobuf", ".dart": "Dart", ".lua": "Lua",
    ".md": "Markdown", ".mdx": "Markdown", ".markdown": "Markdown", ".rst": "reStructuredText",
    ".txt": "Text", ".dockerfile": "Dockerfile", ".m": "Objective-C", ".mm": "Objective-C++",
    ".graphql": "GraphQL", ".gql": "GraphQL", ".gradle": "Gradle", ".tf": "Terraform",
    ".pl": "Perl", ".r": "R", ".clj": "Clojure", ".scala": "Scala", ".zig": "Zig",
    ".hcl": "HCL", ".f90": "Fortran", ".cmake": "CMake", ".ipynb": "Jupyter Notebook",
}

# 关键文件基础分（用于排序：分数高者优先作为生成上下文）
BASE_SCORE = {
    "readme.md": 90, "readme": 85, "readme.txt": 70, "readme.markdown": 70,
    "requirements.txt": 60, "pyproject.toml": 60, "setup.py": 60, "setup.cfg": 50,
    "manage.py": 55, "package.json": 55, "tsconfig.json": 45, "go.mod": 55,
    "go.sum": 5, "cargo.toml": 55, "pom.xml": 55, "build.gradle": 55,
    "dockerfile": 70, "docker-compose.yml": 65, "docker-compose.yaml": 65,
    "makefile": 45, "cmakelists.txt": 45, ".env.example": 45, "config.py": 55,
    "settings.py": 55, "app.py": 55, "main.py": 60, "index.js": 55, "index.ts": 55,
    "index.tsx": 55, "main.go": 55, "wsgi.py": 50, "asgi.py": 50, "alembic.ini": 45,
    "license": 40, "vite.config.ts": 45, "vite.config.js": 45, "webpack.config.js": 45,
    "next.config.js": 40, "entrypoint.sh": 45, "application.py": 55, "__init__.py": 30,
    "models.py": 55, "urls.py": 50, "views.py": 50, "serializers.py": 45,
    "permissions.py": 45, "middleware.py": 45, "admin.py": 40, "routing.py": 45,
}

# 不生成模块页的顶层目录
SKIP_MODULE_DIRS = {
    "docs", "scripts", "test", "tests", ".github", ".vscode", ".idea", "config",
    "cfg", "conf", "examples", "example", "assets", "static", "public", "bin",
    "lib", "vendor", "migrations", "alembic", "build", "dist", "node_modules",
}

MAX_SCANNED_FILES = 8000
MAX_TREE_DEPTH = 6


@dataclass
class FileNode:
    name: str
    path: str  # 相对仓库根
    type: str  # dir / file
    size: int = 0
    language: str = ""
    children: list["FileNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "size": self.size,
            "language": self.language,
            "children": [c.to_dict() for c in self.children] if self.children else [],
        }


@dataclass
class RepoAnalysis:
    repo_id: str
    root: Path
    tree: FileNode
    language_stats: dict[str, dict]
    stats: dict
    key_files: list[Path]  # 相对路径，按重要性降序
    readme_text: str
    modules: list[str]  # 顶层模块目录名
    total_files: int


def _lang_of(name: str) -> str:
    low = name.lower()
    if low == "dockerfile":
        return "Dockerfile"
    if low == "makefile":
        return "Makefile"
    if low == "procfile":
        return "Procfile"
    dot = name.rfind(".")
    if dot == -1:
        return ""
    return EXT_LANG.get(name[dot:].lower(), "")


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            head = f.read(2048)
    except OSError:
        return True
    return b"\x00" in head


def _count_lines(text: str) -> int:
    return text.count("\n") + 1


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    if b"\x00" in raw[:4096]:
        return ""
    for enc in ("utf-8", "gbk", "big5", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="replace")


def _importance_score(name: str, depth: int, lines: int) -> int:
    low = name.lower()
    base = BASE_SCORE.get(low, 0)
    if base == 0:
        # 常见入口/模型的启发式
        if low.startswith(("main", "app", "index", "entry", "cli")) and "." in low:
            base = 45
        elif low in ("__init__.py", "__main__.py"):
            base = 25
    score = base + max(0, 6 - depth) * 3
    if 30 <= lines <= 1500:
        score += 8
    elif lines > 3000:
        score -= 10  # 超长文件反而稀释上下文
    return score


def analyze_repo(repo_id: str, root: Path) -> RepoAnalysis:
    language_stats: dict[str, dict] = {}
    key_files: list[tuple[int, Path]] = []
    total_files = 0
    total_lines = 0
    total_bytes = 0

    def walk(dir_path: Path, rel: str, depth: int, parent: FileNode) -> None:
        nonlocal total_files, total_lines, total_bytes
        if depth > MAX_TREE_DEPTH:
            return
        try:
            entries = sorted(os.scandir(dir_path), key=lambda e: (e.is_file(), e.name.lower()))
        except OSError:
            return
        for entry in entries:
            if len(parent.children) > 500:
                continue
            name = entry.name
            if name in SKIP_DIRS or name in SKIP_FILES:
                continue
            if not entry.is_dir():
                dot = name.rfind(".")
                if dot >= 0 and name[dot:].lower() in SKIP_EXTS:
                    continue
            if entry.is_dir():
                child = FileNode(name=name, path=f"{rel}/{name}" if rel else name, type="dir")
                walk(Path(entry.path), child.path, depth + 1, child)
                if child.children:
                    parent.children.append(child)
            else:
                p = Path(entry.path)
                try:
                    size = p.stat().st_size
                except OSError:
                    continue
                total_files += 1
                total_bytes += size
                lang = _lang_of(name)
                if lang:
                    lines = _count_lines(_read_text(p)) if not _is_binary(p) else 0
                    stat = language_stats.setdefault(lang, {"files": 0, "lines": 0})
                    stat["files"] += 1
                    stat["lines"] += lines
                    total_lines += lines
                    rel_path = f"{rel}/{name}" if rel else name
                    key_files.append((_importance_score(name, depth, lines), p))
                    parent.children.append(
                        FileNode(name=name, path=rel_path, type="file", size=size, language=lang)
                    )
                elif not _is_binary(p):
                    # 无语言但非二进制，仍计入文本文件数
                    total_files += 1
                    rel_path = f"{rel}/{name}" if rel else name
                    parent.children.append(
                        FileNode(name=name, path=rel_path, type="file", size=size)
                    )

    # 使用 scandir 需要导入 os
    import os

    tree_root = FileNode(name=root.name, path="", type="dir")
    if root.exists():
        walk(root, "", 0, tree_root)

    key_files.sort(reverse=True)
    key_files = key_files[:120]
    key_abs = [p for _, p in key_files]

    readme = _find_readme(root)

    top_languages = sorted(
        ({"name": k, "files": v["files"], "lines": v["lines"], "percent": 0.0}
         for k, v in language_stats.items()),
        key=lambda x: x["lines"] or x["files"],
        reverse=True,
    )
    total_lang_lines = sum(l["lines"] for l in top_languages) or 1
    for lang in top_languages:
        lang["percent"] = round(lang["lines"] * 100 / total_lang_lines, 1)

    stats = {
        "files": total_files,
        "lines": total_lines,
        "bytes": total_bytes,
        "dirs": sum(1 for n in _walk_nodes(tree_root) if n.type == "dir"),
        "top_languages": top_languages,
        "key_files": [str(p.relative_to(root)) for p in key_abs],
        "modules": _detect_modules(root, tree_root),
        "generated_at": None,
    }

    return RepoAnalysis(
        repo_id=repo_id,
        root=root,
        tree=tree_root,
        language_stats=language_stats,
        stats=stats,
        key_files=key_abs,  # 绝对路径，供生成器读取文件内容
        readme_text=readme,
        modules=stats["modules"],
        total_files=total_files,
    )


def _walk_nodes(node: FileNode):
    yield node
    for c in node.children:
        yield from _walk_nodes(c)


def _find_readme(root: Path) -> str:
    for cand in ("README.md", "README.markdown", "README.rst", "README.txt", "readme.md", "README"):
        p = root / cand
        if p.exists() and not _is_binary(p):
            try:
                return _read_text(p)
            except OSError:
                return ""
    return ""


def _detect_modules(root: Path, tree: FileNode) -> list[str]:
    """识别顶层模块目录（含源码文件且非公共/配置类目录）。"""
    modules = []
    for child in tree.children:
        if child.type != "dir" or child.name.lower() in SKIP_MODULE_DIRS:
            continue
        src_count = sum(1 for n in _walk_nodes(child) if n.type == "file" and n.language)
        if src_count >= 2:
            modules.append(child.name)
    return modules


# 供其它模块复用的工具
def read_source_text(path: Path, max_chars: int = 40000) -> str:
    text = _read_text(path)
    if len(text) > max_chars:
        # 尽量在行边界截断
        return text[:max_chars] + "\n... [已截断，完整内容见源码]" if False else text[:max_chars] + "\n...(截断)"
    return text


def first_docstring(text: str, limit: int = 600) -> str:
    """提取文件开头的文档字符串/注释/标题，用于静态摘要。"""
    text = text.strip()
    if not text:
        return ""
    lines = text.splitlines()
    summary: list[str] = []
    for line in lines[:40]:
        s = line.strip()
        if not s:
            if summary:
                break
            continue
        if s.startswith(("#", "//", "/*", "*", "--", "\"\"\"", "'''")) or s.startswith("<!--"):
            summary.append(s.lstrip("#/*-\"' ").strip())
        elif summary and s.startswith(("def ", "class ", "import ", "from ", "export", "func ")):
            break
        elif not summary and s.startswith(("def ", "class ", "import ")):
            break
        else:
            if summary:
                break
            continue
    out = " ".join(summary)
    return out[:limit]

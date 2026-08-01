"""将代码仓内容组织成可供 LLM 使用的上下文（带字符预算保护）。"""
import logging
from pathlib import Path

from .analyzer import RepoAnalysis, _walk_nodes, first_docstring, read_source_text

logger = logging.getLogger(__name__)

# 与 schema/数据模型相关的文件名/目录启发式
DATA_HINTS = (
    "models.py", "models/", "schema", "schema.py", "models.js", "type.ts", "types.ts",
    "dto", "entities/", "entity", "database", "db.py", "prisma", "migrations/", "alembic/",
    "sql/", "*.sql", "mongodb", "mysql", "postgres", "sqlalchemy", "pydantic", "zod",
)


def language_summary(analysis: RepoAnalysis) -> str:
    langs = analysis.stats.get("top_languages", [])
    if not langs:
        return "（未识别到主语言）"
    return "、".join(f"{l['name']} {l['percent']}%" for l in langs[:6])


def directory_map(analysis: RepoAnalysis, max_depth: int = 3) -> str:
    """生成 2~3 层的目录结构描述（紧凑）。"""
    lines: list[str] = []

    def render(node, depth: int) -> None:
        if depth > max_depth:
            return
        indent = "  " * depth
        if node.type == "dir":
            lines.append(f"{indent}{node.name}/")
        else:
            lines.append(f"{indent}{node.name}")
        for c in node.children[:80]:
            render(c, depth + 1)

    for c in analysis.tree.children[:120]:
        render(c, 0)
    return "\n".join(lines)


def readme_excerpt(analysis: RepoAnalysis, max_chars: int = 6000) -> str:
    if not analysis.readme_text:
        return ""
    return analysis.readme_text[:max_chars]


def module_files(analysis: RepoAnalysis, module: str) -> list[Path]:
    """模块目录内的源文件（绝对路径），按重要性排序。"""
    hits: list[tuple[int, Path]] = []
    prefix = module + "/"
    for i, p in enumerate(analysis.key_files):
        try:
            rel = str(p.relative_to(analysis.root))
        except ValueError:
            continue
        if rel.startswith(prefix):
            hits.append((len(analysis.key_files) - i, p))
    hits.sort(reverse=True)
    return [p for _, p in hits[:40]]


def data_files(analysis: RepoAnalysis) -> list[Path]:
    """识别疑似数据模型/API 定义文件。"""
    out: list[Path] = []
    for p in analysis.key_files:
        rel = str(p).lower()
        if any(h in rel for h in DATA_HINTS) or p.suffix.lower() == ".sql":
            out.append(p)
        if len(out) >= 20:
            break
    return out


def render_file_blocks(analysis: RepoAnalysis, files: list[Path], per_file: int = 6000, total: int = 40000) -> str:
    """渲染一组文件的代码块文本，受总量限制。"""
    parts: list[str] = []
    used = 0
    for p in files:
        if used >= total:
            break
        text = read_source_text(p, max_chars=per_file)
        if not text.strip():
            continue
        block = f"\n#### 文件：`{p}`\n```\n{text}\n```\n"
        if used + len(block) > total:
            block = block[: total - used]
        parts.append(block)
        used += len(block)
    return "".join(parts)


def file_summaries(analysis: RepoAnalysis, files: list[Path], limit: int = 60) -> str:
    """生成关键文件的一行摘要（用于引用索引页），路径相对仓库根。"""
    lines: list[str] = []
    for p in files[:limit]:
        text = read_source_text(p, max_chars=4000)
        doc = first_docstring(text, limit=200)
        note = f" — {doc}" if doc else ""
        try:
            rel = str(p.relative_to(analysis.root))
        except ValueError:
            rel = str(p)
        lines.append(f"- `{rel}`{note}")
    return "\n".join(lines)


def rel_path(analysis: RepoAnalysis, p: Path) -> str:
    """将绝对路径转为仓库相对路径（展示用）。"""
    try:
        return str(p.relative_to(analysis.root))
    except ValueError:
        return str(p)


def find_tree_node(analysis: RepoAnalysis, rel: str) -> object:
    for n in _walk_nodes(analysis.tree):
        if n.path == rel:
            return n
    return None

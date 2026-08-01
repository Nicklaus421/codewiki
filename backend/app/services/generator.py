"""Wiki 文档生成管线：优先 DeepSeek AI 生成，失败/无 Key 时降级为静态分析兜底。

每个页面独立生成、独立兜底，单页失败不影响整体。
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..config import get_settings
from . import llm
from .analyzer import RepoAnalysis, first_docstring, read_source_text
from .chunker import (
    data_files,
    directory_map,
    file_summaries,
    language_summary,
    module_files,
    readme_excerpt,
    rel_path,
    render_file_blocks,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一名资深软件架构师与文档专家，正在为代码仓库编写高质量的 Wiki 文档。"
    "请用简体中文，输出规范、可读的 Markdown。使用恰当的标题层级（不要从一级标题开始，避免与页面标题重复）、"
    "列表、表格与代码块。内容必须严格基于给定的代码上下文，不得编造不存在的文件、接口或功能。"
    "若某处信息不足，明确标注「仓库中未发现」。"
)


@dataclass
class PageDraft:
    path: str
    title: str
    page_type: str
    content: str
    source: str  # ai / static
    source_files: list[str] = field(default_factory=list)
    order: int = 0


class Generator:
    def __init__(self, analysis: RepoAnalysis):
        self.a = analysis
        self.settings = get_settings()
        self.ai = llm.llm_available()
        if not self.ai:
            logger.info("未配置 DEEPSEEK_API_KEY，使用静态分析生成文档")

    # ---------- 公共工具 ----------
    async def _gen(self, page_type: str, path: str, title: str, ai_user: str, static_fn,
                   files: list[Path] | None = None) -> PageDraft:
        src_files = _source_files(self.a, files)
        if self.ai:
            try:
                content = await llm.complete(SYSTEM_PROMPT, ai_user)
                if content:
                    return PageDraft(path=path, title=title, page_type=page_type,
                                     content=content, source="ai", source_files=src_files)
            except Exception as e:  # noqa: BLE001 单页失败降级
                logger.warning("AI 生成 %s 失败，降级为静态：%s", path, e)
        return PageDraft(path=path, title=title, page_type=page_type,
                         content=static_fn(), source="static", source_files=src_files)

    # ---------- 固定页面 ----------
    async def overview(self) -> PageDraft:
        readme = readme_excerpt(self.a)
        dir_map = directory_map(self.a, max_depth=2)
        langs = language_summary(self.a)
        files = self.a.stats.get("files", 0)
        lines = self.a.stats.get("lines", 0)
        user = (
            f"# 项目概览生成任务\n\n"
            f"## 仓库概况\n- 仓库名：{self.a.root.name}\n- 总文件数：{files}\n- 总代码行数：{lines}\n"
            f"- 主要语言：{langs}\n\n"
            f"## README 内容\n```\n{readme[:6000]}\n```\n\n"
            f"## 目录结构（前两层）\n```\n{dir_map[:8000]}\n```\n\n"
            f"请生成页面「项目概览」，包含：一句话定位、核心功能清单、技术栈、"
            f"项目亮点/特点（基于结构推断），以及「仓库中未发现」的标注。"
        )

        def static():
            lines_out = ["## 项目简介"]
            if readme.strip():
                intro = readme.strip().splitlines()
                lines_out.append(intro[0][:300] if intro else "（README 为空）")
                lines_out.append("")
            lines_out += ["## 技术栈", langs, "", "## 仓库统计",
                          f"- 文件数：{files}", f"- 代码行数：{lines}", "",
                          "## 目录结构", "", "```", dir_map[:4000], "```"]
            return "\n".join(lines_out)

        return await self._gen("overview", "overview", "项目概览", user, static,
                               files=self.a.key_files[:15])

    async def architecture(self) -> PageDraft:
        dir_map = directory_map(self.a, max_depth=4)
        key_files = [str(p) for p in self.a.key_files[:40]]
        user = (
            f"# 架构设计生成任务\n\n## 目录结构（前四层）\n```\n{dir_map[:12000]}\n```\n\n"
            f"## 关键文件清单\n{chr(10).join('- ' + f for f in key_files)}\n\n"
            f"## 关键文件内容\n{render_file_blocks(self.a, self.a.key_files[:10], per_file=5000, total=30000)}\n\n"
            f"请生成页面「架构设计」：描述整体架构风格（如分层/微服务/单体）、模块划分与职责、"
            f"目录组织说明、关键数据流向、模块间依赖关系（基于结构推断），最后是「模块一览」表格"
            f"（模块名 / 职责 / 主要文件）。"
        )

        def static():
            out = ["## 整体结构"]
            for child in self.a.tree.children[:40]:
                out.append(f"- {child.name}/" if child.type == "dir" else f"- {child.name}")
            out += ["", "## 模块一览"]
            for mod in self.a.modules[:10]:
                files_in = [rel_path(self.a, p) for p in module_files(self.a, mod)[:5]]
                out.append(f"- **{mod}**：{len(files_in)} 个源文件" + ("（" + "、".join(files_in[:3]) + "）" if files_in else ""))
            return "\n".join(out)

        return await self._gen("architecture", "architecture", "架构设计", user, static,
                               files=self.a.key_files[:25])

    async def getting_started(self) -> PageDraft:
        readme = readme_excerpt(self.a, 8000)
        top_files = [rel_path(self.a, p) for p in self.a.key_files[:6]]
        cfg_files = [p for p in self.a.key_files if _is_cfg(p)][:8]
        user = (
            f"# 快速开始生成任务\n\n## README\n```\n{readme}\n```\n\n## 配置/入口相关文件\n"
            f"{render_file_blocks(self.a, cfg_files, per_file=4000, total=15000)}\n\n"
            f"请生成页面「快速开始」：环境要求、安装步骤（依赖管理工具命令）、配置方法、启动/运行命令、"
            f"常用命令示例。若 README 已有相关内容，请整理归纳；缺失部分标注「仓库中未发现」。"
        )

        def static():
            return (
                "## 安装\n\n仓库未提供明确的安装脚本，请参考根目录文件（"
                + "、".join(top_files) + "）与 README。\n\n## 运行\n\n请阅读上方「项目概览」或源码入口文件确定启动方式。"
            )

        return await self._gen("getting-started", "getting-started", "快速开始", user, static,
                               files=cfg_files)

    async def data_model(self) -> PageDraft:
        dm_files = data_files(self.a)
        if not dm_files:
            return None
        user = (
            f"# 数据模型/接口生成任务\n\n检测到以下疑似数据模型/API 定义文件：\n"
            f"{chr(10).join('- ' + str(p) for p in dm_files)}\n\n"
            f"## 文件内容\n{render_file_blocks(self.a, dm_files, per_file=6000, total=35000)}\n\n"
            f"请生成页面「数据模型与接口」：列出核心实体/模型及其字段含义、表结构（如有）、"
            f"主要 API 端点（方法/路径/作用）或配置项，使用表格呈现。信息不足处标注「仓库中未发现」。"
        )

        def static():
            out = ["## 相关文件"]
            for p in dm_files[:20]:
                doc = first_docstring(read_source_text(p, 4000), 120)
                out.append(f"- `{rel_path(self.a, p)}`" + (f" — {doc}" if doc else ""))
            return "\n".join(out)

        return await self._gen("data-model", "data-model", "数据模型与接口", user, static,
                               files=dm_files)

    async def module(self, mod: str) -> PageDraft:
        files = module_files(self.a, mod)
        user = (
            f"# 模块文档生成任务\n\n需要为目录 `{mod}/` 编写模块文档。\n\n"
            f"## 目录结构\n```\n{directory_map(self.a, max_depth=4)}\n```\n"
            f"（请重点描述 `{mod}/` 部分）\n\n## 模块源文件\n"
            f"{render_file_blocks(self.a, files, per_file=5000, total=30000)}\n\n"
            f"请生成页面「模块：{mod}」：模块职责、核心类/函数/组件（列名并一句话说明）、"
            f"对外暴露的接口、与其它模块的关系。信息不足处标注「仓库中未发现」。"
        )

        def static():
            out = [f"## 模块职责", f"`{mod}/` 目录包含 {len(files)} 个源文件。", "", "## 主要文件"]
            for p in files[:15]:
                doc = first_docstring(read_source_text(p, 4000), 120)
                out.append(f"- `{rel_path(self.a, p)}`" + (f" — {doc}" if doc else ""))
            return "\n".join(out)

        page = await self._gen("module", f"modules/{mod}", f"模块：{mod}", user, static, files=files)
        return page

    async def references(self) -> PageDraft:
        ref_files = self.a.key_files[:80]
        summaries = file_summaries(self.a, ref_files)
        user = (
            f"# 关键文件索引生成任务\n\n## 关键文件与摘要\n{summaries}\n\n"
            f"请生成页面「关键文件索引」：按目录分组列出关键文件，每个文件一句话说明其作用，"
            f"作为开发者浏览代码的入口索引。用表格或列表呈现。"
        )

        def static():
            return f"## 关键文件\n\n{summaries or '（未识别到关键文件）'}"

        return await self._gen("reference", "references", "关键文件索引", user, static,
                               files=ref_files)

    # ---------- 主入口 ----------
    async def generate(self, progress_cb) -> list[PageDraft]:
        drafts: list[PageDraft] = []
        # 固定顺序页
        fixed = [
            await self.overview(),
            await self.architecture(),
            await self.getting_started(),
        ]
        dm = await self.data_model()
        if dm:
            fixed.append(dm)
        mods = [await self.module(m) for m in self.a.modules[:10]]
        fixed.append(await self.references())

        all_pages = fixed + mods
        for i, d in enumerate(all_pages):
            d.order = i
            if progress_cb:
                await progress_cb(i, len(all_pages), d.path)
        return all_pages


def _source_files(analysis: RepoAnalysis, files: list[Path] | None, limit: int = 50) -> list[str]:
    """将参考源码文件列表归一化为仓库相对路径（去重、限量）。"""
    if not files:
        return []
    out: list[str] = []
    for p in files:
        rel = rel_path(analysis, p)
        if rel and rel not in out:
            out.append(rel)
        if len(out) >= limit:
            break
    return out


def _is_cfg(p: Path) -> bool:
    low = p.name.lower()
    return any(k in low for k in ("readme", "requirement", "pyproject", "package.json", "docker",
                                   "config", "env", "makefile", "cargo.toml", "go.mod"))

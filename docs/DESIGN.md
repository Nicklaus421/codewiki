# 云核软件资产治理平台 — 详细设计文档

> 版本：1.0.0 · 更新日期：2026-08-01

## 1. 项目概述

云核软件资产治理平台是一款面向软件资产的治理服务。核心能力：

1. **按代码仓添加资产**：粘贴任意 git 仓库地址即可入库，平台自动克隆、分析代码仓，形成可治理的软件资产清单。
2. **DeepWiki 风格文档展示**：基于代码仓内容自动生成结构化 Wiki 文档（项目概览、架构设计、快速开始、数据模型/接口、模块文档、关键文件索引），并以 DeepWiki 风格的三栏界面展示；支持全文搜索与源码浏览。
3. **AI 增强 + 静态兜底**：默认调用 DeepSeek（`deepseek-v4-pro`，OpenAI 兼容协议）生成高质量文档；未配置 API Key 或 AI 调用失败时，自动降级为静态分析生成，服务始终可用。
4. **生产可部署**：提供 Docker Compose 与裸机（systemd + Nginx）两套部署方案，开箱即用。

## 2. 系统架构

```
┌─────────────┐
│   浏览器     │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐    /api/* 反向代理     ┌──────────────────────────────┐
│   Nginx     │ ─────────────────────► │          FastAPI 后端          │
│ (前端静态 +  │                        │   /api/repos /api/search ...    │
│  SPA 回退)   │                        │ ┌────────────────────────────┐ │
└─────────────┘                        │ │ 异步任务调度 (asyncio 队列)  │ │
                                       │ │  clone→分析→生成 Wiki        │ │
                                       │ └────────────┬───────────────┘ │
                                       │   ┌──────────▼──────────────┐   │
                                       │   │ DeepSeek (OpenAI 兼容)   │   │
                                       │   └──────────────────────────┘   │
                                       │   ┌────────────────────────────┐ │
                                       │   │ SQLite + FTS5 全文索引      │ │
                                       │   └────────────────────────────┘ │
                                       │   ┌────────────────────────────┐ │
                                       │   │ data/ 仓库源码 + 文档缓存    │ │
                                       │   └────────────────────────────┘ │
                                       └──────────────────────────────┘
```

**单节点拓扑**：Nginx 提供静态资源与 `/api` 反向代理，后端进程内维护异步任务队列执行长耗时任务（克隆/分析/生成），状态全部落库，前端轮询任务进度。

## 3. 技术选型

| 层次 | 技术 | 选型理由 |
|---|---|---|
| 后端 | Python 3.12 + FastAPI | 异步 I/O、LLM 生态成熟、开发效率高 |
| ORM | SQLAlchemy 2.0 (async) | 成熟的异步 ORM，迁移友好 |
| 存储 | SQLite（含 FTS5 全文索引） | 单机部署零运维；WAL 模式支持并发读写；FTS5 支持全文检索 |
| AI | DeepSeek API（OpenAI 兼容） | 用户指定模型 `deepseek-v4-pro`；`openai` SDK 设 `base_url` 即可对接 |
| 任务调度 | 进程内 asyncio 队列 | 单实例简单可靠；文档描述扩展到 Redis/RQ 的方案 |
| 前端 | React 19 + Vite 6 + TypeScript + Tailwind v4 | 组件化、构建快、类型安全 |
| Markdown | react-markdown + remark-gfm + rehype-highlight | GFM 表格 + 代码高亮 |
| 部署 | Docker Compose / systemd + Nginx | 双方案覆盖容器与裸机 |

## 4. 目录结构

```
AssetGovernance/
├── docs/DESIGN.md            # 本设计文档
├── README.md                 # 快速开始
├── docker-compose.yml        # Docker 一键部署
├── .env.example              # 环境变量模板
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py           # FastAPI 入口 / 生命周期 / CORS
│       ├── config.py         # pydantic-settings 配置
│       ├── db.py             # 引擎 / 会话 / FTS5 DDL
│       ├── models.py         # Repository / WikiPage / DocTask
│       ├── schemas.py        # Pydantic 请求/响应
│       ├── api/              # repos / pages / files / search / tasks 路由
│       ├── services/         # git / analyzer / chunker / llm / generator / storage
│       └── tasks/runner.py   # 异步任务调度
├── frontend/
│   ├── Dockerfile            # 多阶段构建 + nginx
│   ├── nginx.conf
│   └── src/
│       ├── pages/            # ReposPage（资产列表）/ RepoView（三栏视图）
│       ├── components/       # Sidebar/FileTree/Markdown/对话框等
│       ├── api/client.ts     # 后端 API 客户端
│       └── lib/              # hooks / 格式化工具
└── deploy/baremetal/         # systemd 单元 / Nginx 配置 / install.sh
```

## 5. 数据模型

### repositories — 代码仓资产
| 字段 | 类型 | 说明 |
|---|---|---|
| id | str(32) | UUID hex 主键 |
| name | str | 资产显示名（由 URL 推导或自定义） |
| url | str | git 仓库地址（唯一索引） |
| branch / default_branch | str | 指定分支 / 探测到的默认分支 |
| status | str | pending → cloning → analyzing → generating → ready / failed |
| error | text | 失败原因 |
| source_path | str | 本地克隆路径 |
| language_stats | json | 语言统计 {语言: {files, lines}} |
| stats | json | 文件数/行数/字节数/顶层语言占比/key_files/modules/generated_at |

### wiki_pages — 生成的文档页
| 字段 | 类型 | 说明 |
|---|---|---|
| id | int | 主键（FTS5 rowid） |
| repo_id | str(32, FK, 索引) | 所属仓库 |
| path | str | 页面路径（overview / architecture / modules/xxx） |
| title | str | 页面标题 |
| page_type | str | overview / architecture / getting-started / data-model / module / reference |
| source | str | `ai`（AI 生成）/ `static`（静态兜底） |
| content | text | Markdown 正文 |
| source_files | json | 生成时参考的文件清单 |
| order | int | 排序 |
| UNIQUE(repo_id, path) | — | 页面唯一 |

### doc_tasks — 任务进度
id / repo_id / kind(add|regenerate) / status(pending|running|done|failed) / step / progress(0-100) / message。

### FTS5 全文索引
`wiki_pages_fts`（external content 表，`content='wiki_pages'`, `tokenize='unicode61'`）。中文子串搜索由 LIKE 兜底覆盖。详见「9. 搜索实现」。

## 6. API 规范

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/repos | 添加代码仓资产 {url, branch?} → 202 {id, task_id} |
| GET | /api/repos | 资产列表（含状态、统计、页面数） |
| GET | /api/repos/{id} | 资产详情 + 顶层文件树 |
| DELETE | /api/repos/{id} | 删除资产（级联清理页面/任务/本地源码） |
| POST | /api/repos/{id}/regenerate | 重新克隆并生成文档 → 202 {task_id} |
| GET | /api/repos/{id}/pages | 文档页面导航列表 |
| GET | /api/repos/{id}/pages/{path} | 页面 Markdown 内容 |
| GET | /api/repos/{id}/tree?path= | 目录条目（懒加载） |
| GET | /api/repos/{id}/file?path= | 源码文件内容（含语言识别、大小限制） |
| GET | /api/search?q=&repo_id= | 全文搜索（FTS5 + LIKE 兜底） |
| GET | /api/tasks/{task_id} | 任务进度 |
| GET | /api/health | 健康检查 |

## 7. 文档生成管线

以仓库为单位执行：**克隆 → 分析 → 生成 → 持久化**，全程异步、进度落库。

### 7.1 克隆（git_service）
- `git clone --depth 1 --single-branch` 浅克隆，支持指定分支；探测 `origin/HEAD` 得到默认分支。
- 大小上限校验（默认 200MB），超限即失败。
- URL 正则校验，避免任意命令注入；仓库名从 URL 推导并清洗。

### 7.2 分析（analyzer）
- 递归遍历源码树，跳过 `.git / node_modules / dist / build / __pycache__` 等噪音目录与常见二进制/锁文件扩展名；深度与文件数设有上限（防超大仓库拖垮内存）。
- 语言统计：按扩展名映射语言，累计文件数与代码行数，计算占比。
- 关键文件识别：README、构建/配置/入口/数据模型等文件赋予重要性分数（名称 + 深度 + 行数加权），排序后截取 Top N，作为生成上下文与索引页素材。
- 模块识别：顶层含 ≥2 个源文件、非公共/配置/文档目录的目录视为模块，为每个模块生成独立页面。

### 7.3 上下文构建（chunker）
- 按页面类型挑选相关文件（概览→README；架构→目录结构与入口；数据模型→schema/model/sql 文件；模块→该目录文件）。
- 字符预算保护：单文件与总上下文均设上限（如单文件 6K、总量 30–40K 字符），超长文件在行边界截断，避免 token 超限。

### 7.4 AI 生成（llm + generator）
- 通过 `openai` SDK 指向 `DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com`），模型 `DEEPSEEK_MODEL`（默认 `deepseek-v4-pro`）。
- 每个页面独立调用、独立兜底；带超时（180s）、重试（2 次）、并发限制（默认 2）与页级异常隔离——单页失败不影响整体任务。
- 生成页面集：项目概览、架构设计、快速开始、数据模型与接口（按检测情况）、`modules/*` 模块页、关键文件索引。
- Prompt 约束：使用简体中文 Markdown、不得编造仓库中不存在的文件/接口、信息不足时标注「仓库中未发现」。

### 7.5 静态兜底（无 Key / AI 失败）
- 概览：README 摘要 + 技术栈 + 仓库统计 + 目录结构。
- 架构：目录结构 + 模块一览（含文件清单）。
- 模块页：目录内源文件 + 首行文档注释/标题摘要。
- 索引页：关键文件 + 首行摘要，路径均展示为仓库相对路径（不泄漏服务器绝对路径）。
- 页面标记 `source=static`，前端展示「静态生成」徽标，用户可感知降级状态。

### 7.6 持久化
- 事务内清空旧页面 → 写入新页面 → 重建 FTS 索引 → 更新仓库 `ready` 状态与统计（含 `generated_at`、`page_count`）。
- 任务进度 0→100 实时回写，前端轮询展示。

## 8. 前端设计

**DeepWiki 风格**：深色顶栏与侧栏（`#0d1117`）+ 浅色内容区，左侧导航树，右侧正文阅读。

### 8.1 资产列表（/）
- 资产卡片：名称、仓库地址、状态徽章（克隆中/分析中/生成中/已就绪/失败）、统计（文件/行/页）、语言占比标签。
- 操作：添加代码仓（对话框内实时任务进度条）、重新生成、删除（二次确认）。
- Cmd/Ctrl+K 打开全局搜索。

### 8.2 三栏文档视图（/repos/:id）
- 顶部：资产名、状态、文件/行/页统计、重建按钮（含进度）。
- 左栏：**文档**导航（AI 生成页带 ✨ 标识，静态页带 📖 标识）+ **源码**文件树（懒加载，可折叠）。
- 主区：面包屑 + 页面标题 + AI/静态徽标 + 参考文件（可点击跳转源码）+ Markdown 渲染（GFM 表格、代码高亮）。
- 点击文件树中的文件 → 源码查看弹窗（语言高亮、Esc 关闭）。

### 8.3 全局搜索
- Cmd/Ctrl+K 唤起；输入 ≥2 字符防抖查询；命中列表展示标题 + 仓库 + 摘要片段；点击跳转对应页面。

## 9. 搜索实现

- 首选 FTS5（external content 表 + `unicode61` tokenizer）：英文/数字词命中即按 BM25 相关度排序。
- 中文/短查询兜底：FTS 无命中或查询 <3 字符时回退 `LIKE` 模糊匹配（`content.contains`），覆盖中文子串场景。
- **实现说明**：本环境 SQLite 的 FTS5 `delete` 命令不可用（含 trigram/unicode61），故采用 external content 表 + 页面变更后整体 `rebuild` 的方式维护索引；在数据规模（每仓数页）下重建开销可忽略。

## 10. 安全设计

- **路径穿越防护**：源码/文件接口通过 `resolve_source_path` 将相对路径锚定到仓库根，拒绝 `../`。
- **命令注入防护**：git 参数全部列表化传递（无 shell 拼接）；分支名白名单正则校验。
- **URL 校验**：仅接受 http/https/ssh/git 形式的仓库地址。
- **文件读取保护**：二进制检测、编码兜底、单文件返回大小上限、HTML 转义（源码查看）。
- **密钥管理**：`DEEPSEEK_API_KEY` 仅存环境变量/.env，不入库不入码。
- **部署加固**：systemd `NoNewPrivileges / ProtectSystem / ReadWritePaths / PrivateTmp`；前端资源长缓存。

## 11. 部署方案

### 11.1 Docker Compose（推荐，单机生产）

```bash
cd AssetGovernance
cp .env.example .env        # 编辑填写 DEEPSEEK_API_KEY
docker compose up -d --build
# 访问 http://<服务器IP>:8080
```

- `backend`：gunicorn + uvicorn worker（`APP_WORKERS` 默认 1，保证进程内任务队列可预测），`./data` 卷持久化，healthcheck。
- `web`：多阶段构建前端 → nginx 提供静态资源并代理 `/api` → `backend:8000`。

### 11.2 裸机部署（systemd + Nginx）

```bash
cd deploy/baremetal
sudo bash install.sh
```

- install.sh：创建运行用户 → 复制代码 → 后端 venv + pip install → 前端 npm 构建 → 生成 `.env` → 安装 `yunhe-backend.service` → 配置 Nginx 站点。
- 手动步骤见 README「裸机部署」。

### 11.3 环境变量（.env）

```
DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL   # LLM
DATA_DIR / DATABASE_URL                                  # 存储
APP_HOST / APP_PORT / APP_WORKERS / LOG_LEVEL            # 服务
MAX_REPO_SIZE_MB / CLONE_TIMEOUT                          # 仓库约束
LLM_TIMEOUT / LLM_MAX_RETRIES / LLM_CONCURRENCY           # AI 鲁棒性
CORS_ORIGINS                                              # 跨域
```

## 12. 运维与监控

- **健康检查**：`GET /api/health`，Docker healthcheck 与监控探针复用。
- **日志**：结构化访问日志（uvicorn/gunicorn），`journalctl -u yunhe-backend -f` 查看。
- **数据备份**：备份 `data/` 目录（含 SQLite 与仓库源码），SQLite 已启用 WAL。
- **任务恢复**：任务状态持久化于 DB，进程重启后失败任务可见（`failed`），可手动「重建」。

## 13. 扩展性设计

| 场景 | 演进方案 |
|---|---|
| 任务量大 / 高并发生成 | 将 `tasks/runner.py` 任务体迁移至 Redis + RQ/Celery，worker 独立扩容 |
| 多实例横向扩展 | 后端无状态化 + 共享存储（NFS/S3 放置源码）+ Postgres 替代 SQLite |
| 大仓库分析 | 引入 `git clone --filter=blob:none` + Lazy Tree 分析，进一步限制文件数 |
| 搜索体验 | 集成 OpenSearch/Meilisearch，支持分面与相关度调参 |
| 鉴权 | 前置网关或集成 OIDC 登录（当前为内网信任模型） |

## 14. 测试与验收

| 场景 | 预期 |
|---|---|
| `POST /api/repos` 添加 `CoreGeekASTL/AIAction` | 返回 202 与 task_id，任务进度可达 100 |
| 任务完成后 `GET /api/repos/{id}/pages` | ≥6 个页面（概览/架构/快速开始/数据模型/索引/模块） |
| 配置 DEEPSEEK_API_KEY | 页面 `source=ai`，内容为 AI 生成 |
| 清空 DEEPSEEK_API_KEY | 页面 `source=static`，服务仍可用 |
| `/api/search?q=` 英文词 | FTS5 命中；中文短词走 LIKE 兜底 |
| 删除资产 | 页面/任务/本地源码级联清理 |
| 生产代理链路 | Nginx → /api → 后端 全链路 200 |

## 15. 已知局限与后续规划

- 单 worker 内执行任务，重负载时可扩展 Redis/RQ。
- FTS5 对中文做整词索引，子串搜索依赖 LIKE 兜底（数据量大时可换搜索引擎）。
- 默认信任内网访问，如需公网暴露建议前置鉴权。
- 模块页面按「顶层目录」粒度生成，后续可支持任意深度模块与文件级文档。

# 云核软件资产治理平台

按代码仓添加软件资产，自动生成并展示 DeepWiki 风格的文档（项目概览、架构、快速开始、数据模型、模块文档、关键文件索引）。文档默认由 **DeepSeek AI**（`deepseek-v4-pro`）生成，未配置 API Key 时自动降级为静态分析，服务始终可用。

> 详细设计见 [docs/DESIGN.md](docs/DESIGN.md)。

## 功能特性

- **按代码仓添加资产**：粘贴 git 地址即可，自动克隆 → 分析 → 生成 Wiki 文档
- **DeepWiki 风格界面**：三栏布局（文档导航 + 源码树 + Markdown 正文）、Cmd+K 全局搜索、源码浏览高亮
- **AI + 静态兜底**：DeepSeek 生成，失败/无 Key 自动降级
- **生产可部署**：Docker Compose 或裸机（systemd + Nginx）

## 快速开始（本地开发）

前置：Python ≥ 3.10、Node ≥ 20、git。

```bash
# 1. 启动后端
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
# （可选）启用 AI 生成：export DEEPSEEK_API_KEY=sk-xxx

# 2. 启动前端（另开终端）
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### 添加示例资产

在页面点击「添加代码仓」，填入：

```
https://github.com/CoreGeekASTL/AIAction.git
```

或直接调用 API：

```bash
curl -X POST http://127.0.0.1:8000/api/repos \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://github.com/CoreGeekASTL/AIAction.git"}'
```

## Docker Compose 部署（生产）

```bash
cp .env.example .env      # 编辑填写 DEEPSEEK_API_KEY（可选，留空则静态兜底）
docker compose up -d --build
# 访问 http://<服务器IP>:8080
```

- 数据持久化在宿主机 `./data`（SQLite + 仓库源码）。
- 单独重建镜像：`docker compose build backend web`。

## 裸机部署（systemd + Nginx）

```bash
cd deploy/baremetal
sudo bash install.sh
```

install.sh 会自动创建运行用户、安装依赖、构建前端、配置 systemd 与 Nginx。手动部署步骤：

```bash
# 后端
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # 编辑 DEEPSEEK_API_KEY
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

# 前端
cd frontend && npm install && npm run build
# Nginx 站点配置参考 deploy/baremetal/nginx.conf（root 指向 frontend/dist，/api 反代 127.0.0.1:8000）
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| DEEPSEEK_API_KEY | 空 | DeepSeek API Key；留空走静态兜底 |
| DEEPSEEK_BASE_URL | https://api.deepseek.com | OpenAI 兼容端点 |
| DEEPSEEK_MODEL | deepseek-v4-pro | 生成模型 |
| DATA_DIR | data | 数据目录（源码 + DB） |
| DATABASE_URL | 空（自动派生） | 自定义数据库连接串 |
| APP_PORT / APP_WORKERS | 8000 / 1 | 服务端口 / worker 数 |
| MAX_REPO_SIZE_MB | 200 | 单仓大小上限 |
| CORS_ORIGINS | * | 跨域白名单 |

## 主要 API

```
POST   /api/repos                     添加代码仓（返回 task_id）
GET    /api/repos                     资产列表
GET    /api/repos/{id}/pages          文档页面列表
GET    /api/repos/{id}/pages/{path}   页面内容
GET    /api/search?q=                 全文搜索
GET    /api/tasks/{task_id}           任务进度
DELETE /api/repos/{id}                删除资产
```

## 目录结构

```
backend/   FastAPI 后端（API + 服务层 + 任务调度）
frontend/  React 前端（Vite + Tailwind）
docs/      设计文档
deploy/    裸机部署（systemd + Nginx + install.sh）
docker-compose.yml
```

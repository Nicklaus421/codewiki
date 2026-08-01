"""云核软件资产治理平台 — FastAPI 应用入口。"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import files, pages, repos, search, tasks
from .config import get_settings
from .db import create_tables, init_db

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await create_tables()
    logger.info("%s 已启动", get_settings().app_name)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router, prefix="/api/repos", tags=["repos"])
app.include_router(pages.router, prefix="/api/repos", tags=["pages"])
app.include_router(files.router, prefix="/api/repos", tags=["files"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }

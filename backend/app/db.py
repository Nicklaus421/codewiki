"""数据库初始化：SQLAlchemy(async) + SQLite，并维护 FTS5 全文索引（trigram，支持中文子串匹配）。"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

logger = logging.getLogger(__name__)

# FTS5 全文索引（external content 表）。
# 说明：本环境 SQLite 的 FTS5 'delete' 命令不可用（含 trigram/unicode61），
# 因此采用 external content 表 + 'rebuild' 命令，在页面变更后整体重建索引；
# 索引规模小（每仓数页），重建开销可忽略。中文子串搜索由 LIKE 兜底覆盖。
FTS_DDL = [
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS wiki_pages_fts USING fts5(
        title, content,
        content='wiki_pages',
        content_rowid='id',
        tokenize='unicode61'
    )
    """,
]


class Base(DeclarativeBase):
    pass


_engine = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_db() -> None:
    global _engine, _session_maker
    settings = get_settings()
    settings.resolved_data_dir.mkdir(parents=True, exist_ok=True)
    _engine = create_async_engine(
        settings.resolved_database_url,
        echo=False,
        pool_pre_ping=True,
    )
    _session_maker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    if _session_maker is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    return _session_maker


async def create_tables() -> None:
    from . import models  # noqa: F401  确保模型已注册到 Base.metadata

    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in FTS_DDL:
            await conn.execute(text(stmt))
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA foreign_keys=ON;"))
    logger.info("数据库表与全文索引已就绪")


async def get_session():
    maker = get_session_maker()
    async with maker() as session:
        yield session

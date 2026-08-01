"""ORM 模型：Repository（资产）、WikiPage（生成的文档页）、DocTask（任务进度）。"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _new_id() -> str:
    return uuid.uuid4().hex


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1024), index=True)
    branch: Mapped[str] = mapped_column(String(128), default="")
    default_branch: Mapped[str] = mapped_column(String(128), default="")
    # pending / cloning / analyzing / generating / ready / failed
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error: Mapped[str] = mapped_column(Text, default="")
    source_path: Mapped[str] = mapped_column(String(1024), default="")
    language_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    pages: Mapped[list["WikiPage"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["DocTask"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


class WikiPage(Base):
    __tablename__ = "wiki_pages"
    __table_args__ = (UniqueConstraint("repo_id", "path", name="uq_wiki_repo_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(String(255))  # overview / architecture / modules/xxx ...
    title: Mapped[str] = mapped_column(String(255))
    page_type: Mapped[str] = mapped_column(String(64), default="page")
    # ai / static
    source: Mapped[str] = mapped_column(String(16), default="static")
    content: Mapped[str] = mapped_column(Text, default="")
    source_files: Mapped[list] = mapped_column(JSON, default=list)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    repository: Mapped["Repository"] = relationship(back_populates="pages")


class DocTask(Base):
    __tablename__ = "doc_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    repo_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32), default="add")  # add / regenerate
    # pending / running / done / failed
    status: Mapped[str] = mapped_column(String(32), default="pending")
    step: Mapped[str] = mapped_column(String(64), default="")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    repository: Mapped["Repository"] = relationship(back_populates="tasks")

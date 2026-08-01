"""Pydantic 请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class RepoCreate(BaseModel):
    url: str = Field(..., min_length=4, max_length=1024, description="git 仓库地址（http/https/ssh）")
    branch: str | None = Field(None, max_length=128, description="指定分支（可选，默认使用仓库默认分支）")
    name: str | None = Field(None, max_length=255, description="资产显示名（可选）")


class RepoAddResponse(BaseModel):
    id: str
    task_id: str
    status: str


class PageSummary(BaseModel):
    id: int
    path: str
    title: str
    page_type: str
    source: str
    order: int
    updated_at: datetime


class PageContent(PageSummary):
    content: str
    source_files: list[str] = []


class FileEntry(BaseModel):
    name: str
    path: str
    type: str  # dir / file
    size: int = 0
    children: list["FileEntry"] = []


FileEntry.model_rebuild()


class RepoListItem(BaseModel):
    id: str
    name: str
    url: str
    branch: str
    default_branch: str
    status: str
    error: str = ""
    language_stats: dict = {}
    stats: dict = {}
    page_count: int = 0
    created_at: datetime
    updated_at: datetime


class RepoDetail(RepoListItem):
    top_tree: list[FileEntry] = []


class TaskOut(BaseModel):
    id: str
    repo_id: str
    kind: str
    status: str
    step: str
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime


class SearchHit(BaseModel):
    repo_id: str
    repo_name: str
    path: str
    title: str
    snippet: str


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class HealthOut(BaseModel):
    status: str
    app: str
    version: str

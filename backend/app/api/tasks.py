"""任务进度查询（前端轮询）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import DocTask
from ..schemas import TaskOut

router = APIRouter()


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)):
    task = await session.get(DocTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskOut(
        id=task.id, repo_id=task.repo_id, kind=task.kind, status=task.status,
        step=task.step, progress=task.progress, message=task.message,
        created_at=task.created_at, updated_at=task.updated_at,
    )

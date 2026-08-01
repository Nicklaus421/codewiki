import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { TaskOut } from '../types';

/** 全局快捷键：Cmd/Ctrl + key */
export function useHotkey(keys: string[], cb: () => void) {
  const cbRef = useRef(cb);
  cbRef.current = cb;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && keys.includes(e.key.toLowerCase())) {
        e.preventDefault();
        cbRef.current();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [keys]);
}

const PENDING_STUB = (taskId: string): TaskOut => ({
  id: taskId,
  repo_id: '',
  kind: 'add',
  status: 'pending',
  step: '',
  progress: 0,
  message: '等待任务开始...',
  created_at: '',
  updated_at: '',
});

/** 任务进度轮询 */
export function useTaskPoll(taskId: string | null, onDone?: (repoId: string) => void) {
  const [task, setTask] = useState<TaskOut | null>(taskId ? PENDING_STUB(taskId) : null);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    if (!taskId) {
      setTask(null);
      return;
    }
    let cancelled = false;
    let iv: number | undefined;
    const poll = async () => {
      try {
        const res = await api.getTask(taskId);
        if (cancelled) return;
        setTask(res);
        if (res.status === 'done') {
          if (iv) clearInterval(iv);
          onDoneRef.current?.(res.repo_id);
        } else if (res.status === 'failed') {
          if (iv) clearInterval(iv);
        }
      } catch {
        /* 轮询失败忽略 */
      }
    };
    poll();
    iv = window.setInterval(poll, 1500);
    return () => {
      cancelled = true;
      if (iv) clearInterval(iv);
    };
  }, [taskId]);

  return task;
}

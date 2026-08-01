import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, GitBranch, Github, Loader2, X } from 'lucide-react';
import { api } from '../api/client';
import { useTaskPoll } from '../lib/hooks';

const EXAMPLE = 'https://github.com/CoreGeekASTL/AIAction.git';

export default function AddRepoDialog({
  open,
  onClose,
  onAdded,
}: {
  open: boolean;
  onClose: () => void;
  onAdded: (repoId: string) => void;
}) {
  const [url, setUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const urlRef = useRef<HTMLInputElement>(null);

  const task = useTaskPoll(taskId, onAdded);

  useEffect(() => {
    if (open) {
      setUrl('');
      setBranch('');
      setError(null);
      setTaskId(null);
      setSubmitting(false);
      requestAnimationFrame(() => urlRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const submit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.addRepo(url.trim(), branch.trim() || undefined);
      setTaskId(res.task_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setSubmitting(false);
    }
  };

  const busy = !!(task && (task.status === 'running' || task.status === 'pending'));
  const done = task?.status === 'done';

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/40 px-4 pt-[14vh] backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
          <h2 className="text-sm font-semibold text-slate-800">添加代码仓资产</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-4 px-5 py-4">
          <div>
            <label className="mb-1 flex items-center gap-1.5 text-xs font-medium text-slate-600">
              <Github size={13} /> Git 仓库地址
            </label>
            <input
              ref={urlRef}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={EXAMPLE}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              disabled={busy || done}
            />
            <button
              type="button"
              onClick={() => setUrl(EXAMPLE)}
              className="mt-1 text-[11px] text-indigo-500 hover:underline"
            >
              使用示例仓库：{EXAMPLE}
            </button>
          </div>

          <div>
            <label className="mb-1 flex items-center gap-1.5 text-xs font-medium text-slate-600">
              <GitBranch size={13} /> 分支（可选，默认使用仓库默认分支）
            </label>
            <input
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              disabled={busy || done}
            />
          </div>

          {error && (
            <div className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">{error}</div>
          )}

          {task && !done && (
            <div className="rounded-lg bg-slate-50 px-3 py-3">
              <div className="flex items-center justify-between text-xs text-slate-600">
                <span className="font-medium">{task.message}</span>
                <span>{task.progress}%</span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                  style={{ width: `${task.progress}%` }}
                />
              </div>
            </div>
          )}

          {done && (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2.5 text-sm text-emerald-700">
              <CheckCircle2 size={16} /> 文档生成完成，正在跳转...
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3.5">
          {!done && (
            <>
              <button
                onClick={onClose}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
                disabled={busy}
              >
                取消
              </button>
              <button
                onClick={submit}
                disabled={submitting || !url.trim() || !!busy}
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting && <Loader2 size={14} className="animate-spin" />}
                {busy ? '处理中...' : '添加并生成文档'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

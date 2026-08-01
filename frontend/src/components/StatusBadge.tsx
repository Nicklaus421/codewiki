import type { RepoStatus } from '../types';
import { REPO_STATUS_LABEL } from '../lib/format';

const STYLES: Record<RepoStatus, string> = {
  pending: 'bg-slate-100 text-slate-600 border-slate-200',
  cloning: 'bg-sky-50 text-sky-700 border-sky-200',
  analyzing: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  generating: 'bg-amber-50 text-amber-700 border-amber-200',
  ready: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  failed: 'bg-rose-50 text-rose-700 border-rose-200',
};

const DOTS: Record<RepoStatus, string> = {
  pending: 'bg-slate-400',
  cloning: 'bg-sky-500',
  analyzing: 'bg-indigo-500',
  generating: 'bg-amber-500',
  ready: 'bg-emerald-500',
  failed: 'bg-rose-500',
};

export default function StatusBadge({ status }: { status: RepoStatus }) {
  const busy = status === 'cloning' || status === 'analyzing' || status === 'generating';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${DOTS[status]} ${busy ? 'animate-pulse' : ''}`}
      />
      {REPO_STATUS_LABEL[status]}
    </span>
  );
}

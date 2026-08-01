import { useCallback, useEffect, useState } from 'react';
import {
  BookOpen,
  FileCode2,
  GitFork,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import AddRepoDialog from '../components/AddRepoDialog';
import SearchDialog from '../components/SearchDialog';
import StatusBadge from '../components/StatusBadge';
import TopBar from '../components/TopBar';
import { useHotkey, useTaskPoll } from '../lib/hooks';
import { formatNumber, langColor } from '../lib/format';
import type { RepoListItem } from '../types';

export default function ReposPage() {
  const [repos, setRepos] = useState<RepoListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    try {
      setError(null);
      setRepos(await api.listRepos());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  useHotkey(['k'], () => setSearchOpen(true));

  return (
    <div className="flex h-full flex-col bg-slate-50">
      <TopBar onOpenSearch={() => setSearchOpen(true)} />
      <main className="flex-1 overflow-y-auto thin-scroll">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-800">软件资产</h1>
              <p className="mt-1 text-sm text-slate-500">
                按代码仓添加资产，AI 自动生成 DeepWiki 风格的文档
              </p>
            </div>
            <button
              onClick={() => setAddOpen(true)}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
            >
              <Plus size={16} /> 添加代码仓
            </button>
          </div>

          {error && (
            <div className="mb-4 flex items-center justify-between rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-600">
              <span>后端连接失败：{error}</span>
              <button onClick={load} className="flex items-center gap-1 text-xs underline">
                <RefreshCw size={12} /> 重试
              </button>
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center gap-2 py-20 text-sm text-slate-400">
              <Loader2 size={18} className="animate-spin" /> 加载中...
            </div>
          )}

          {!loading && repos.length === 0 && !error && (
            <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white py-20 text-center">
              <BookOpen size={36} className="text-slate-300" />
              <p className="text-sm text-slate-500">还没有资产，点击右上角「添加代码仓」开始</p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {repos.map((r) => (
              <RepoCard
                key={r.id}
                repo={r}
                onChanged={() => setRefreshKey((k) => k + 1)}
              />
            ))}
          </div>
        </div>
      </main>

      <AddRepoDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onAdded={(repoId) => {
          setAddOpen(false);
          window.location.href = `/repos/${repoId}`;
        }}
      />
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}

function RepoCard({ repo, onChanged }: { repo: RepoListItem; onChanged: () => void }) {
  const [regTaskId, setRegTaskId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);

  const task = useTaskPoll(regTaskId, () => {
    setRegTaskId(null);
    onChanged();
  });

  const regenerate = async () => {
    setBusy(true);
    try {
      const res = await api.regenerate(repo.id);
      setRegTaskId(res.task_id);
    } catch {
      setBusy(false);
    }
  };

  const remove = async () => {
    await api.deleteRepo(repo.id);
    onChanged();
  };

  const langs = (repo.stats.top_languages ?? []).slice(0, 3);
  const busyNow = busy || regTaskId !== null;

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="flex items-start justify-between gap-2">
        <Link
          to={`/repos/${repo.id}`}
          className="truncate text-sm font-semibold text-slate-800 hover:text-indigo-600"
          title={repo.name}
        >
          {repo.name}
        </Link>
        <StatusBadge status={repo.status} />
      </div>
      <p className="mt-1 truncate font-mono text-xs text-slate-400" title={repo.url}>
        {repo.url.replace(/^https?:\/\//, '').replace(/\.git$/, '')}
      </p>

      <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
        <span className="flex items-center gap-1 rounded bg-slate-50 px-1.5 py-0.5 text-slate-500">
          <FileCode2 size={11} /> {formatNumber(repo.stats.files ?? 0)} 文件
        </span>
        <span className="flex items-center gap-1 rounded bg-slate-50 px-1.5 py-0.5 text-slate-500">
          <GitFork size={11} /> {formatNumber(repo.stats.lines ?? 0)} 行
        </span>
        <span className="flex items-center gap-1 rounded bg-indigo-50 px-1.5 py-0.5 text-indigo-500">
          <BookOpen size={11} /> {repo.page_count} 页
        </span>
      </div>

      {langs.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {langs.map((l) => (
            <span
              key={l.name}
              className="flex items-center gap-1 rounded-full bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600"
            >
              <span className="h-2 w-2 rounded-full" style={{ background: langColor(l.name) }} />
              {l.name} {l.percent}%
            </span>
          ))}
        </div>
      )}

      {task && task.status !== 'done' && (
        <div className="mt-3 rounded bg-slate-50 px-2 py-2">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span className="truncate">{task.message}</span>
            <span className="shrink-0 pl-2">{task.progress}%</span>
          </div>
          <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${task.progress}%` }}
            />
          </div>
        </div>
      )}

      {repo.status === 'failed' && repo.error && (
        <p className="mt-2 line-clamp-2 text-[11px] text-rose-500">{repo.error}</p>
      )}

      <div className="mt-3 flex items-center gap-2 border-t border-slate-100 pt-3">
        <Link
          to={`/repos/${repo.id}`}
          className="rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-100"
        >
          查看文档
        </Link>
        <button
          onClick={regenerate}
          disabled={busyNow || repo.status === 'pending'}
          className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-100 disabled:opacity-40"
          title="重新克隆并生成文档"
        >
          {busyNow ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          重建
        </button>
        <div className="flex-1" />
        {confirmDel ? (
          <span className="flex items-center gap-1">
            <button
              onClick={remove}
              className="rounded-lg bg-rose-50 px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-100"
            >
              确认删除
            </button>
            <button onClick={() => setConfirmDel(false)} className="p-1 text-slate-400 hover:text-slate-600">
              <X size={13} />
            </button>
          </span>
        ) : (
          <button
            onClick={() => setConfirmDel(true)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-500"
            title="删除资产"
          >
            <Trash2 size={15} />
          </button>
        )}
      </div>
    </div>
  );
}

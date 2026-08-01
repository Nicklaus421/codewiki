import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  BookOpen,
  Bot,
  ChevronRight,
  FileCode2,
  FileText,
  Home,
  Loader2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import FileViewer from '../components/FileViewer';
import MDFileTree from '../components/MDFileTree';
import { Markdown } from '../components/Markdown';
import SearchDialog from '../components/SearchDialog';
import StatusBadge from '../components/StatusBadge';
import TopBar from '../components/TopBar';
import { useHotkey, useTaskPoll } from '../lib/hooks';
import { formatTime } from '../lib/format';
import type { PageContent, PageSummary, RepoListItem } from '../types';

const toPageUrl = (repoId: string, p: string) =>
  `/repos/${repoId}/page/${p.split('/').map(encodeURIComponent).join('/')}`;

function parsePagePath(wildcard: string | undefined): string {
  const rest = (wildcard ?? '').replace(/^page\/?/, '');
  if (!rest) return 'overview';
  return rest
    .split('/')
    .map((s) => {
      try {
        return decodeURIComponent(s);
      } catch {
        return s;
      }
    })
    .join('/');
}

export default function RepoView() {
  const params = useParams();
  const repoId = params.repoId ?? '';
  const navigate = useNavigate();

  const pagePath = parsePagePath(params['*']);

  const [repo, setRepo] = useState<RepoListItem | null>(null);
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [page, setPage] = useState<PageContent | null>(null);
  const [loadingRepo, setLoadingRepo] = useState(true);
  const [loadingPage, setLoadingPage] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [regTaskId, setRegTaskId] = useState<string | null>(null);

  const regTask = useTaskPoll(regTaskId, () => {
    setRegTaskId(null);
    loadRepo();
    loadPages();
    loadPage();
  });

  const loadRepo = useCallback(async () => {
    try {
      const r = await api.getRepo(repoId);
      setRepo(r);
      setNotFound(false);
    } catch {
      setNotFound(true);
    } finally {
      setLoadingRepo(false);
    }
  }, [repoId]);

  const loadPages = useCallback(async () => {
    try {
      setPages(await api.getPages(repoId));
    } catch {
      /* ignore */
    }
  }, [repoId]);

  const loadPage = useCallback(async () => {
    setLoadingPage(true);
    try {
      setPage(await api.getPage(repoId, pagePath));
    } catch {
      setPage(null);
    } finally {
      setLoadingPage(false);
    }
  }, [repoId, pagePath]);

  useEffect(() => {
    setLoadingRepo(true);
    setLoadingPage(true);
    setNotFound(false);
    loadRepo();
    loadPages();
  }, [repoId, loadRepo, loadPages]);

  useEffect(() => {
    loadPage();
  }, [pagePath, loadPage]);

  useHotkey(['k'], () => setSearchOpen(true));

  const pageMeta = useMemo(() => pages.find((p) => p.path === pagePath), [pages, pagePath]);

  if (loadingRepo) {
    return (
      <div className="flex h-full flex-col bg-slate-50">
        <TopBar onOpenSearch={() => setSearchOpen(true)} />
        <div className="flex flex-1 items-center justify-center gap-2 text-sm text-slate-400">
          <Loader2 size={18} className="animate-spin" /> 加载中...
        </div>
      </div>
    );
  }

  if (notFound || !repo) {
    return (
      <div className="flex h-full flex-col bg-slate-50">
        <TopBar onOpenSearch={() => setSearchOpen(true)} />
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-sm text-slate-500">
          <BookOpen size={36} className="text-slate-300" />
          <p>仓库不存在或已被删除</p>
          <Link to="/" className="text-indigo-600 hover:underline">
            返回资产列表
          </Link>
        </div>
      </div>
    );
  }

  const regenerate = async () => {
    try {
      const res = await api.regenerate(repo.id);
      setRegTaskId(res.task_id);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="flex h-full flex-col bg-white">
      <TopBar onOpenSearch={() => setSearchOpen(true)} />

      <div className="flex min-h-0 flex-1">
        {/* 左侧导航 */}
        <aside className="flex w-72 shrink-0 flex-col border-r border-slate-800 bg-[#0d1117]">
          <div className="border-b border-slate-800 px-4 py-3">
            <div className="flex items-center justify-between gap-2">
              <button
                onClick={() => navigate('/')}
                className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-300"
              >
                <Home size={12} /> 资产列表
              </button>
              <button
                onClick={regenerate}
                disabled={regTaskId !== null}
                className="flex items-center gap-1 rounded-md bg-slate-800 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-700 disabled:opacity-50"
                title="重新克隆并生成文档"
              >
                {regTaskId !== null ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <RefreshCw size={12} />
                )}
                重建
              </button>
            </div>
            <h1 className="mt-2 truncate text-base font-bold text-white" title={repo.name}>
              {repo.name}
            </h1>
            <div className="mt-1.5 flex items-center gap-2">
              <StatusBadge status={repo.status} />
              <span className="truncate text-[11px] text-slate-500">
                {repo.stats.files ?? 0} 文件 · {repo.stats.lines ?? 0} 行 · {pages.length} 页
              </span>
            </div>
            {regTask && regTask.status !== 'done' && (
              <div className="mt-2">
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span className="truncate">{regTask.message}</span>
                  <span className="pl-2">{regTask.progress}%</span>
                </div>
                <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                    style={{ width: `${regTask.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto thin-scroll">
            <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              文档
            </div>
            <nav className="px-2 pb-2">
              {pages.map((p) => {
                const active = p.path === pagePath;
                return (
                  <button
                    key={p.path}
                    onClick={() => navigate(toPageUrl(repo.id, p.path))}
                    className={`flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-left text-[13px] ${
                      active
                        ? 'bg-indigo-500/15 text-indigo-300'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                    }`}
                    title={p.title}
                  >
                    {p.source === 'ai' ? (
                      <Sparkles size={13} className="shrink-0 text-amber-400" />
                    ) : (
                      <BookOpen size={13} className="shrink-0 text-slate-500" />
                    )}
                    <span className="truncate">{p.title}</span>
                  </button>
                );
              })}
            </nav>

            <div className="flex items-center gap-1 px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              <FileText size={11} /> Markdown 文档
            </div>
            <MDFileTree repoId={repo.id} />
          </div>
        </aside>

        {/* 主内容区 */}
        <main className="min-w-0 flex-1 overflow-y-auto thin-scroll bg-slate-50">
          <div className="mx-auto max-w-4xl px-8 py-6">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Link to="/" className="hover:text-indigo-500">
                资产
              </Link>
              <ChevronRight size={12} />
              <Link to={`/repos/${repo.id}`} className="hover:text-indigo-500">
                {repo.name}
              </Link>
              <ChevronRight size={12} />
              <span className="text-slate-600">{pageMeta?.title ?? pagePath}</span>
            </div>

            {loadingPage ? (
              <div className="flex items-center justify-center gap-2 py-24 text-sm text-slate-400">
                <Loader2 size={18} className="animate-spin" /> 加载页面...
              </div>
            ) : !page ? (
              <div className="flex flex-col items-center gap-2 py-24 text-sm text-slate-400">
                <BookOpen size={32} className="text-slate-300" />
                <p>页面「{pagePath}」不存在</p>
              </div>
            ) : (
              <article className="mt-4 rounded-xl border border-slate-200 bg-white px-8 py-7 shadow-sm">
                <div className="mb-5 flex items-start justify-between gap-3 border-b border-slate-100 pb-4">
                  <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                    {page.title}
                  </h1>
                  <SourceBadge source={page.source} />
                </div>

                {page.source_files.length > 0 && (
                  <div className="mb-5 rounded-lg bg-slate-50 px-4 py-3 text-xs text-slate-500">
                    <div className="mb-1.5 font-medium text-slate-600">参考文件</div>
                    <ul className="space-y-1">
                      {page.source_files.slice(0, 20).map((f) => (
                        <li key={f} className="flex items-center gap-1.5">
                          <FileCode2 size={12} className="shrink-0 text-slate-400" />
                          <button
                            onClick={() => setFilePath(f)}
                            className="truncate font-mono text-indigo-500 hover:underline"
                            title={`查看 ${f}`}
                          >
                            {f}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <Markdown content={page.content} />

                <footer className="mt-8 border-t border-slate-100 pt-3 text-xs text-slate-400">
                  更新于 {formatTime(page.updated_at)} · 路径 {page.path}
                </footer>
              </article>
            )}
          </div>
        </main>
      </div>

      <FileViewer repoId={repo.id} path={filePath} onClose={() => setFilePath(null)} />
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}

function SourceBadge({ source }: { source: string }) {
  const cfg =
    source === 'ai'
      ? {
          cls: 'bg-amber-50 text-amber-600',
          title: '由 DeepSeek AI 生成',
          label: 'AI 生成',
          Icon: Bot,
        }
      : source === 'md'
        ? {
            cls: 'bg-indigo-50 text-indigo-600',
            title: '源码中的 Markdown 文档',
            label: '源码文档',
            Icon: FileText,
          }
        : {
            cls: 'bg-slate-100 text-slate-500',
            title: '由静态分析生成（未配置 DEEPSEEK_API_KEY 或 AI 生成失败）',
            label: '静态生成',
            Icon: FileCode2,
          };
  return (
    <span
      className={`flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${cfg.cls}`}
      title={cfg.title}
    >
      <cfg.Icon size={11} />
      {cfg.label}
    </span>
  );
}

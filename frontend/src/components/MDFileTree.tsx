import { useCallback, useState } from 'react';
import { ChevronRight, FileText, Folder, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { FileEntry } from '../types';

// 只展示 docs/ 目录下的 Markdown 文档，且不展示 docs 节点本身
const DOCS_ROOT = 'docs';

const isMd = (name: string) => /\.md$/i.test(name);

function filterMd(entries: FileEntry[]): FileEntry[] {
  // 后端 only_md 已剪枝，这里仅做兜底过滤
  return entries.filter((e) => e.type === 'dir' || isMd(e.name));
}

const toPageUrl = (repoId: string, p: string) =>
  `/repos/${repoId}/page/${p.split('/').map(encodeURIComponent).join('/')}`;

function MDTreeNode({
  repoId,
  entry,
  depth,
  onOpen,
}: {
  repoId: string;
  entry: FileEntry;
  depth: number;
  onOpen: (path: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [children, setChildren] = useState<FileEntry[] | null>(null);
  const [loading, setLoading] = useState(false);

  const toggle = useCallback(async () => {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (children === null) {
      setLoading(true);
      try {
        const data = await api.getTree(repoId, entry.path, true);
        setChildren(filterMd(data.entries ?? []));
      } catch {
        setChildren([]);
      } finally {
        setLoading(false);
      }
    }
  }, [open, children, repoId, entry.path]);

  if (entry.type === 'file') {
    return (
      <button
        onClick={() => onOpen(entry.path)}
        title={entry.path}
        className="flex w-full items-center gap-1.5 truncate rounded px-2 py-[3px] text-left text-[13px] text-slate-300 hover:bg-slate-800/60 hover:text-white"
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
      >
        <FileText size={13} className="shrink-0 text-indigo-400" />
        <span className="truncate">{entry.name}</span>
      </button>
    );
  }

  return (
    <div>
      <button
        onClick={toggle}
        title={entry.path}
        className="flex w-full items-center gap-1.5 rounded px-2 py-[3px] text-left text-[13px] font-medium text-slate-300 hover:bg-slate-800/60 hover:text-white"
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
      >
        <ChevronRight
          size={13}
          className={`shrink-0 text-slate-500 transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <Folder size={13} className="shrink-0 text-amber-500" />
        <span className="truncate">{entry.name}</span>
        {loading && <Loader2 size={12} className="ml-auto animate-spin text-slate-500" />}
      </button>
      {open && (
        <div>
          {children === null && <div className="h-6" />}
          {(children ?? []).map((c) => (
            <MDTreeNode
              key={c.path}
              repoId={repoId}
              entry={c}
              depth={depth + 1}
              onOpen={onOpen}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function MDFileTree({ repoId }: { repoId: string }) {
  const [entries, setEntries] = useState<FileEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  if (entries === null && error === null) {
    api
      .getTree(repoId, DOCS_ROOT, true)
      .then((d) => setEntries(filterMd(d.entries ?? [])))
      .catch((e) => {
        // docs 目录不存在时视为无文档，不报错
        if (e instanceof ApiError && e.status === 404) setEntries([]);
        else setError(String(e));
      });
  }

  if (error) return <p className="px-3 py-2 text-xs text-rose-500">{error}</p>;
  if (entries === null) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-slate-400">
        <Loader2 size={13} className="animate-spin" /> 加载中...
      </div>
    );
  }
  if (entries.length === 0) {
    return <p className="px-3 py-2 text-xs text-slate-500">未找到 Markdown 文档</p>;
  }
  return (
    <div className="pb-3">
      {entries.map((e) => (
        <MDTreeNode
          key={e.path}
          repoId={repoId}
          entry={e}
          depth={0}
          onOpen={(path) => navigate(toPageUrl(repoId, path))}
        />
      ))}
    </div>
  );
}

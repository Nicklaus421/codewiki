import { useEffect, useMemo, useState } from 'react';
import hljs from 'highlight.js/lib/common';
import { FileCode2, Loader2, X } from 'lucide-react';
import { api } from '../api/client';
import { formatBytes } from '../lib/format';

export default function FileViewer({
  repoId,
  path,
  onClose,
}: {
  repoId: string;
  path: string | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<{
    name: string;
    language: string;
    size: number;
    content: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!path) return;
    setData(null);
    setError(null);
    api
      .getFile(repoId, path)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [repoId, path]);

  useEffect(() => {
    if (!path) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [path, onClose]);

  const html = useMemo(() => {
    if (!data) return '';
    try {
      return hljs.highlight(data.content, {
        language: data.language.toLowerCase(),
        ignoreIllegals: true,
      }).value;
    } catch {
      return data.content.replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' })[c]!);
    }
  }, [data]);

  if (!path) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4 py-8 backdrop-blur-sm">
      <div className="flex h-full w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-slate-700 bg-white shadow-2xl">
        <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
          <FileCode2 size={15} className="text-slate-400" />
          <span className="truncate font-mono text-sm text-slate-700">{path}</span>
          {data && (
            <span className="shrink-0 text-[11px] text-slate-400">
              {data.language || 'text'} · {formatBytes(data.size)}
            </span>
          )}
          <div className="flex-1" />
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-auto thin-scroll bg-[#0d1117]">
          {error && (
            <div className="flex h-full items-center justify-center text-sm text-rose-400">
              {error}
            </div>
          )}
          {!data && !error && (
            <div className="flex h-full items-center justify-center gap-2 text-sm text-slate-400">
              <Loader2 size={16} className="animate-spin" /> 加载源码...
            </div>
          )}
          {data && (
            <pre className="p-4">
              <code
                className="hljs text-[13px] leading-relaxed"
                dangerouslySetInnerHTML={{ __html: html }}
              />
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

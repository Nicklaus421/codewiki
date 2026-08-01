import { useEffect, useRef, useState } from 'react';
import { FileText, Loader2, Search, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { SearchHit } from '../types';

export default function SearchDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (open) {
      setQ('');
      setHits([]);
      setSearched(false);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const qs = q.trim();
    if (qs.length < 2) {
      setHits([]);
      setSearched(false);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const res = await api.search(qs);
        if (!cancelled) {
          setHits(res.hits);
          setSearched(true);
        }
      } catch {
        if (!cancelled) setHits([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q, open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const go = (repoId: string, path: string) => {
    onClose();
    navigate(
      `/repos/${repoId}/page/${path.split('/').map(encodeURIComponent).join('/')}`,
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/40 px-4 pt-[12vh] backdrop-blur-sm">
      <div className="w-full max-w-xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
          <Search size={16} className="text-slate-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索 Wiki 文档内容（如：登录、controller、架构）"
            className="flex-1 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
          />
          {loading ? (
            <Loader2 size={14} className="animate-spin text-slate-400" />
          ) : (
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
              <X size={16} />
            </button>
          )}
        </div>
        <div className="max-h-[50vh] overflow-y-auto thin-scroll">
          {!searched && !loading && (
            <p className="px-4 py-8 text-center text-xs text-slate-400">
              输入至少 2 个字符开始搜索
            </p>
          )}
          {searched && hits.length === 0 && (
            <p className="px-4 py-8 text-center text-xs text-slate-400">
              未找到与「{q.trim()}」相关的文档
            </p>
          )}
          {hits.map((h) => (
            <button
              key={`${h.repo_id}-${h.path}`}
              onClick={() => go(h.repo_id, h.path)}
              className="block w-full border-b border-slate-50 px-4 py-3 text-left hover:bg-slate-50"
            >
              <div className="flex items-center gap-2 text-sm">
                <FileText size={14} className="shrink-0 text-indigo-400" />
                <span className="font-medium text-slate-800">{h.title}</span>
                <span className="ml-auto shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                  {h.repo_name}
                </span>
              </div>
              <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-500">
                {h.snippet}
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

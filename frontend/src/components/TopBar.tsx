import { Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function TopBar({ onOpenSearch }: { onOpenSearch: () => void }) {
  const navigate = useNavigate();
  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-slate-800 bg-[#0d1117] px-4 text-slate-100">
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 text-sm font-semibold tracking-wide hover:text-white"
      >
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-violet-600 text-[11px] font-bold text-white">
          云
        </span>
        <span className="hidden sm:inline">云核软件资产治理平台</span>
      </button>
      <div className="flex-1" />
      <button
        onClick={onOpenSearch}
        className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-600 hover:text-white"
      >
        <Search size={13} />
        <span>搜索文档</span>
        <kbd className="rounded border border-slate-600 bg-slate-900 px-1 text-[10px] text-slate-400">
          ⌘K
        </kbd>
      </button>
    </header>
  );
}

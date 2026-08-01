import type { RepoStatus, TaskStatus } from '../types';

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function formatNumber(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万`;
  return n.toLocaleString('zh-CN');
}

export function formatTime(iso: string): string {
  if (!iso) return '-';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('zh-CN', { hour12: false });
}

export const REPO_STATUS_LABEL: Record<RepoStatus, string> = {
  pending: '等待中',
  cloning: '克隆中',
  analyzing: '分析中',
  generating: '生成中',
  ready: '已就绪',
  failed: '失败',
};

export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  pending: '等待中',
  running: '执行中',
  done: '已完成',
  failed: '失败',
};

export function langColor(name: string): string {
  // 常见语言主题色（仅用于标识）
  const map: Record<string, string> = {
    Go: '#00ADD8',
    Python: '#3572A5',
    TypeScript: '#3178c6',
    JavaScript: '#f1e05a',
    Java: '#b07219',
    Rust: '#dea584',
    'C++': '#f34b7d',
    C: '#555555',
    Shell: '#89e051',
    SQL: '#e38c00',
    HTML: '#e34c26',
    CSS: '#563d7c',
    Vue: '#41b883',
    YAML: '#cb171e',
    JSON: '#292929',
    Dockerfile: '#384d54',
    Markdown: '#083fa1',
  };
  return map[name] || '#8b949e';
}

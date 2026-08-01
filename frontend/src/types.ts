export type RepoStatus =
  | 'pending'
  | 'cloning'
  | 'analyzing'
  | 'generating'
  | 'ready'
  | 'failed';

export interface LanguageStat {
  name: string;
  files: number;
  lines: number;
  percent: number;
}

export interface RepoStats {
  files?: number;
  lines?: number;
  bytes?: number;
  dirs?: number;
  top_languages?: LanguageStat[];
  key_files?: string[];
  modules?: string[];
  generated_at?: string | null;
  page_count?: number;
}

export interface RepoListItem {
  id: string;
  name: string;
  url: string;
  branch: string;
  default_branch: string;
  status: RepoStatus;
  error: string;
  language_stats: Record<string, { files: number; lines: number }>;
  stats: RepoStats;
  page_count: number;
  created_at: string;
  updated_at: string;
}

export interface FileEntry {
  name: string;
  path: string;
  type: 'dir' | 'file';
  size: number;
  language?: string;
}

export interface PageSummary {
  id: number;
  path: string;
  title: string;
  page_type: string;
  source: 'ai' | 'static';
  order: number;
  updated_at: string;
}

export interface PageContent extends PageSummary {
  content: string;
  source_files: string[];
}

export type TaskStatus = 'pending' | 'running' | 'done' | 'failed';

export interface TaskOut {
  id: string;
  repo_id: string;
  kind: string;
  status: TaskStatus;
  step: string;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
}

export interface SearchHit {
  repo_id: string;
  repo_name: string;
  path: string;
  title: string;
  snippet: string;
}

export interface AddRepoResult {
  id: string;
  task_id: string;
  status: string;
}

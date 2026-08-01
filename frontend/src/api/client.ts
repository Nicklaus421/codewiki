import type {
  AddRepoResult,
  FileEntry,
  PageContent,
  PageSummary,
  RepoListItem,
  SearchHit,
  TaskOut,
} from '../types';

const BASE = '/api';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  listRepos: () => req<RepoListItem[]>('/repos'),

  addRepo: (url: string, branch?: string) =>
    req<AddRepoResult>('/repos', json('POST', { url, branch })),

  getRepo: (id: string) => req<RepoListItem & { top_tree: FileEntry[] }>(`/repos/${id}`),

  deleteRepo: (id: string) => req<void>(`/repos/${id}`, { method: 'DELETE' }),

  regenerate: (id: string) => req<AddRepoResult>(`/repos/${id}/regenerate`, { method: 'POST' }),

  getPages: (id: string) => req<PageSummary[]>(`/repos/${id}/pages`),

  getPage: (id: string, path: string) =>
    req<PageContent>(`/repos/${id}/pages/${encodeURIComponent(path)}`),

  getTree: (id: string, path = '', onlyMd = false) =>
    req<{ path: string; entries: FileEntry[] }>(
      `/repos/${id}/tree?path=${encodeURIComponent(path)}${onlyMd ? '&only_md=true' : ''}`,
    ),

  getFile: (id: string, path: string) =>
    req<{ path: string; name: string; language: string; size: number; content: string }>(
      `/repos/${id}/file?path=${encodeURIComponent(path)}`,
    ),

  getTask: (id: string) => req<TaskOut>(`/tasks/${id}`),

  search: (q: string, repoId?: string) =>
    req<{ query: string; hits: SearchHit[] }>(
      `/search?q=${encodeURIComponent(q)}${repoId ? `&repo_id=${encodeURIComponent(repoId)}` : ''}`,
    ),
};

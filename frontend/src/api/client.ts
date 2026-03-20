import type { MediaRoot, ReadingProgress, ScanResult, Settings, Tag, Work } from '../types'

const jsonHeaders = {
  'Content-Type': 'application/json',
}

async function parseResponse<T>(response: Response, message: string): Promise<T> {
  if (!response.ok) {
    throw new Error(message)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export async function fetchWorks(params?: { type?: string; tag?: string }): Promise<Work[]> {
  const search = new URLSearchParams()
  if (params?.type) search.set('type', params.type)
  if (params?.tag) search.set('tag', params.tag)
  const suffix = search.toString() ? `?${search.toString()}` : ''
  const response = await fetch(`/api/works${suffix}`)
  return parseResponse<Work[]>(response, 'Failed to load works')
}

export async function fetchWork(id: string | number): Promise<Work> {
  const response = await fetch(`/api/works/${id}`)
  return parseResponse<Work>(response, 'Failed to load work details')
}

export async function fetchReadingProgress(id: string | number): Promise<ReadingProgress | null> {
  const response = await fetch(`/api/progress/${id}`)
  if (response.status === 404) {
    throw new Error('Work not found')
  }
  return parseResponse<ReadingProgress | null>(response, 'Failed to load reading progress')
}

export async function saveReadingProgress(
  id: string | number,
  input: Pick<ReadingProgress, 'chapter_key' | 'file_index' | 'page' | 'position'>,
): Promise<ReadingProgress> {
  const response = await fetch(`/api/progress/${id}`, {
    method: 'PUT',
    headers: jsonHeaders,
    body: JSON.stringify(input),
  })
  return parseResponse<ReadingProgress>(response, 'Failed to save reading progress')
}

export async function triggerScan(): Promise<ScanResult> {
  const response = await fetch('/api/scan', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({}),
  })
  return parseResponse<ScanResult>(response, 'Failed to trigger scan')
}

export async function fetchSettings(): Promise<Settings> {
  const response = await fetch('/api/settings')
  return parseResponse<Settings>(response, 'Failed to load settings')
}

export async function createMediaRoot(path: string): Promise<MediaRoot> {
  const response = await fetch('/api/settings/media-roots', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ path }),
  })
  return parseResponse<MediaRoot>(response, 'Failed to create media root')
}

export async function deleteMediaRoot(id: number): Promise<void> {
  const response = await fetch(`/api/settings/media-roots/${id}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error('Failed to delete media root')
  }
}

export async function fetchTags(): Promise<Tag[]> {
  const response = await fetch('/api/tags')
  return parseResponse<Tag[]>(response, 'Failed to load tags')
}

export async function createTag(input: { name: string; color?: string; group_name?: string }): Promise<Tag> {
  const response = await fetch('/api/tags', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(input),
  })
  return parseResponse<Tag>(response, 'Failed to create tag')
}

export async function deleteTag(id: number): Promise<void> {
  const response = await fetch(`/api/tags/${id}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error('Failed to delete tag')
  }
}

export async function exportSidecar(id: number): Promise<{ sidecar_path: string }> {
  const response = await fetch(`/api/works/${id}/export-sidecar`, { method: 'POST' })
  return parseResponse(response, 'Failed to export sidecar')
}

export async function importSidecar(id: number): Promise<{ sidecar_path: string }> {
  const response = await fetch(`/api/works/${id}/import-sidecar`, { method: 'POST' })
  return parseResponse(response, 'Failed to import sidecar')
}

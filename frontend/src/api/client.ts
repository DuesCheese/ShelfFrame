import type { ActivityEventType, MediaRoot, RecentActivity, ScanResult, Settings, Tag, Work } from '../types'

const jsonHeaders = {
  'Content-Type': 'application/json',
}

async function parseResponse<T>(response: Response, message: string): Promise<T> {
  if (!response.ok) {
    throw new Error(message)
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

export async function generateThumbnails(id: number, force = false): Promise<{ work_id: number; generated: number }> {
  const suffix = force ? '?force=true' : ''
  const response = await fetch(`/api/works/${id}/generate-thumbnails${suffix}`, { method: 'POST' })
  return parseResponse(response, 'Failed to generate thumbnails')
}

export async function updateWorkCover(id: number, thumbnailId: number): Promise<Work> {
  const response = await fetch(`/api/works/${id}/cover`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ thumbnail_id: thumbnailId }),
  })
  return parseResponse(response, 'Failed to update cover')
}

export async function trackWorkAccess(id: number, eventType: ActivityEventType): Promise<void> {
  const response = await fetch('/api/activity-events', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ work_id: id, event_type: eventType }),
  })
  if (!response.ok) {
    throw new Error('Failed to record access event')
  }
}

export async function fetchRecentActivity(limit = 8): Promise<RecentActivity[]> {
  const response = await fetch(`/api/activity-events/recent?limit=${limit}`)
  return parseResponse(response, 'Failed to load recent activity')
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

export type WorkType = 'comic' | 'video'
export type ScanTaskStatus = 'running' | 'succeeded' | 'completed_with_errors' | 'failed'
export type ScanLogLevel = 'info' | 'warning' | 'error'

export interface MediaFile {
  id: number
  name: string
  path: string
  kind: string
  size_bytes: number | null
  order_index: number
}

export interface Tag {
  id: number
  name: string
  color?: string | null
  group_name?: string | null
}

export interface Work {
  id: number
  title: string
  path: string
  type: WorkType
  summary?: string | null
  cover_path?: string | null
  created_at: string
  updated_at: string
  tags: Tag[]
  files: MediaFile[]
}

export interface ScanLog {
  id: number
  level: ScanLogLevel
  code?: string | null
  path?: string | null
  message: string
  created_at: string
}

export interface ScanTask {
  id: number
  root_path: string
  status: ScanTaskStatus
  started_at: string
  finished_at?: string | null
  error_message?: string | null
  discovered: number
  created: number
  updated: number
  skipped: number
  logs: ScanLog[]
}

export interface ScanRunResult {
  discovered: number
  created: number
  updated: number
  skipped: number
  roots: string[]
  tasks: ScanTask[]
}

export interface MediaRoot {
  id: number
  path: string
  enabled: boolean
}

export interface Settings {
  database_url: string
  media_roots: MediaRoot[]
}

export type WorkType = 'comic' | 'video'
export type ReaderMode = 'scroll' | 'paged'
export type ReaderDirection = 'ltr' | 'rtl'

export interface MediaFile {
  id: number
  name: string
  path: string
  kind: string
  size_bytes: number | null
  order_index: number
  content_url?: string | null
}

export interface Tag {
  id: number
  name: string
  color?: string | null
  group_name?: string | null
}

export interface ReadingProgress {
  work_id: number
  chapter_key?: string | null
  file_index: number
  page: number
  position: number
  updated_at: string
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
  progress?: ReadingProgress | null
}

export interface ScanResult {
  discovered: number
  created: number
  updated: number
  skipped: number
  roots: string[]
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

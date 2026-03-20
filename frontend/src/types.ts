export type WorkType = 'comic' | 'video'

export interface MediaFile {
  id: number
  name: string
  path: string
  kind: string
  size_bytes: number | null
  order_index: number
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
  files: MediaFile[]
}

export interface ScanResult {
  discovered: number
  created: number
  updated: number
  skipped: number
}

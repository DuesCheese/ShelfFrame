export type WorkType = 'comic' | 'video'
export type ThumbnailType = 'cover' | 'keyframe'
export type ActivityEventType = 'detail_open' | 'reader_open' | 'player_open'

export interface MediaFile {
  id: number
  name: string
  path: string
  kind: string
  size_bytes: number | null
  order_index: number
}

export interface Thumbnail {
  id: number
  type: ThumbnailType
  source_path?: string | null
  image_path: string
  ts_sec?: number | null
  sort_no: number
  thumbnail_url: string
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
  cover_url?: string | null
  created_at: string
  updated_at: string
  tags: Tag[]
  files: MediaFile[]
  thumbnails: Thumbnail[]
  current_cover?: Thumbnail | null
}

export interface RecentActivity {
  work: Work
  last_event: {
    id: number
    work_id: number
    event_type: ActivityEventType
    at_time: string
    payload_json?: string | null
  }
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

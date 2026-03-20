export type WorkType = 'comic' | 'video'
export type PlaybackEventType = 'play' | 'seek'

export interface MediaFile {
  id: number
  name: string
  path: string
  kind: string
  size_bytes: number | null
  order_index: number
  content_url?: string | null
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

export interface VideoChapter {
  label: string
  start_seconds: number
  end_seconds: number
}

export interface HoverThumbnail {
  time_seconds: number
  image_url: string
  width?: number | null
  height?: number | null
}

export interface HoverThumbnailManifest {
  status: string
  items: HoverThumbnail[]
}

export interface HeatmapBucket {
  start_seconds: number
  end_seconds: number
  intensity: number
  event_count: number
}

export interface VideoPlayerMetadata {
  source_url?: string | null
  chapters: VideoChapter[]
  hover_thumbnails: HoverThumbnailManifest
  heatmap: HeatmapBucket[]
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
  player_metadata?: VideoPlayerMetadata | null
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

<template>
  <section class="page" v-if="work">
    <header class="page__header">
      <div>
        <p class="eyebrow">视频播放器</p>
        <h2>{{ work.title }}</h2>
        <p>{{ work.summary || '支持章节、时间轴标记、hover thumbnail 接口位与最小可用热度图聚合。' }}</p>
      </div>
    </header>

    <p v-if="loadError" class="panel panel--danger">{{ loadError }}</p>
    <p v-else-if="metadataError" class="panel panel--danger">{{ metadataError }}</p>

    <div class="player-shell">
      <section class="player-main panel">
        <div v-if="primaryFile" class="player-surface">
          <video
            ref="videoRef"
            class="player-video"
            controls
            preload="metadata"
            :src="videoSourceUrl"
            @loadedmetadata="handleLoadedMetadata"
            @timeupdate="handleTimeUpdate"
            @play="handlePlay"
          >
            您的浏览器暂不支持原生视频播放。
          </video>

          <div class="timeline-card">
            <div
              class="timeline-preview"
              v-if="preview.visible"
              :style="{ left: `${preview.leftPercent}%` }"
            >
              <img
                v-if="preview.thumbnail?.image_url"
                :src="preview.thumbnail.image_url"
                alt="hover thumbnail"
              />
              <div v-else class="timeline-preview__placeholder">
                {{ hoverThumbnailLabel }}
              </div>
              <strong>{{ formatTime(preview.timeSeconds) }}</strong>
            </div>

            <div
              class="timeline-track"
              @mousemove="handleTimelineHover"
              @mouseleave="hidePreview"
            >
              <div class="timeline-heatmap" v-if="playerMetadata.heatmap.length">
                <span
                  v-for="bucket in playerMetadata.heatmap"
                  :key="`${bucket.start_seconds}-${bucket.end_seconds}`"
                  class="timeline-heatmap__segment"
                  :style="{
                    opacity: Math.max(bucket.intensity, 0.12).toString(),
                    flex: `${Math.max(bucket.end_seconds - bucket.start_seconds, 0.5)}`,
                  }"
                  :title="`${formatTime(bucket.start_seconds)} - ${formatTime(bucket.end_seconds)} · ${bucket.event_count} 次事件`"
                />
              </div>

              <div class="timeline-markers" v-if="duration > 0 && playerMetadata.chapters.length">
                <button
                  v-for="chapter in playerMetadata.chapters"
                  :key="chapter.label + chapter.start_seconds"
                  class="timeline-marker"
                  type="button"
                  :style="{ left: `${(chapter.start_seconds / duration) * 100}%` }"
                  :title="`${chapter.label} · ${formatTime(chapter.start_seconds)}`"
                  @click="jumpToChapter(chapter.start_seconds)"
                />
              </div>

              <input
                class="timeline-slider"
                type="range"
                min="0"
                :max="duration || 0"
                :step="0.1"
                :value="currentTime"
                :disabled="!duration"
                @input="handleSeekInput"
              />
            </div>

            <div class="player-meta-row">
              <span>{{ formatTime(currentTime) }}</span>
              <span>{{ duration ? formatTime(duration) : '等待元数据' }}</span>
            </div>
          </div>
        </div>
        <div v-else class="player-shell__surface">暂无视频文件</div>
      </section>

      <aside class="player-sidebar stack">
        <section class="panel">
          <h3>章节</h3>
          <ul v-if="playerMetadata.chapters.length" class="chapter-list">
            <li v-for="chapter in playerMetadata.chapters" :key="chapter.label + chapter.start_seconds">
              <button type="button" class="chapter-list__button" @click="jumpToChapter(chapter.start_seconds)">
                <span>{{ chapter.label }}</span>
                <small>{{ formatTime(chapter.start_seconds) }} - {{ formatTime(chapter.end_seconds) }}</small>
              </button>
            </li>
          </ul>
          <p v-else class="panel__muted">暂无章节，可在 sidecar 的 video.chapters 中补充。</p>
        </section>

        <section class="panel">
          <h3>元数据</h3>
          <dl class="meta-list">
            <div>
              <dt>媒体路径</dt>
              <dd>{{ primaryFile?.path || '未配置' }}</dd>
            </div>
            <div>
              <dt>文件大小</dt>
              <dd>{{ fileSizeLabel }}</dd>
            </div>
            <div>
              <dt>标签</dt>
              <dd>{{ tagLabel }}</dd>
            </div>
            <div>
              <dt>更新时间</dt>
              <dd>{{ new Date(work.updated_at).toLocaleString() }}</dd>
            </div>
          </dl>
        </section>

        <section class="panel">
          <h3>Hover Thumbnail</h3>
          <p>接口状态：{{ playerMetadata.hover_thumbnails.status || 'pending' }}</p>
          <p class="panel__muted">
            后端返回结构：time_seconds → image_url；当前前端已完成 UI 接口层，后续可直接接入真实缩略图。
          </p>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { buildMediaFileUrl, createPlaybackEvent, fetchPlayerMetadata, fetchWork } from '../api/client'
import type { HoverThumbnail, VideoPlayerMetadata, Work } from '../types'

const route = useRoute()
const work = ref<Work | null>(null)
const loadError = ref('')
const metadataError = ref('')
const currentTime = ref(0)
const duration = ref(0)
const videoRef = ref<HTMLVideoElement | null>(null)
const preview = ref({ visible: false, leftPercent: 0, timeSeconds: 0, thumbnail: null as HoverThumbnail | null })

const emptyPlayerMetadata: VideoPlayerMetadata = {
  source_url: null,
  chapters: [],
  hover_thumbnails: {
    status: 'pending',
    items: [],
  },
  heatmap: [],
}

const playerMetadata = ref<VideoPlayerMetadata>(emptyPlayerMetadata)
const primaryFile = computed(() => work.value?.files[0] ?? null)
const videoSourceUrl = computed(() => playerMetadata.value.source_url || (primaryFile.value ? buildMediaFileUrl(primaryFile.value.id) : ''))
const tagLabel = computed(() => (work.value?.tags.length ? work.value.tags.map((tag) => tag.name).join('、') : '暂无标签'))
const fileSizeLabel = computed(() => {
  const size = primaryFile.value?.size_bytes
  if (!size) return '未知'
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
})
const hoverThumbnailLabel = computed(() => {
  if (playerMetadata.value.hover_thumbnails.items.length) return '已命中缩略图'
  return playerMetadata.value.hover_thumbnails.status === 'ready' ? '暂无可用缩略图' : '缩略图待生成'
})

async function loadPage() {
  loadError.value = ''
  metadataError.value = ''

  try {
    const loadedWork = await fetchWork(route.params.id as string)
    work.value = loadedWork
    playerMetadata.value = loadedWork.player_metadata ?? emptyPlayerMetadata

    if (loadedWork.type === 'video') {
      try {
        playerMetadata.value = await fetchPlayerMetadata(loadedWork.id)
      } catch (error) {
        metadataError.value = error instanceof Error ? `${error.message}，已回退到基础信息展示。` : '播放器元数据加载失败。'
      }
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Failed to load player page'
  }
}

function formatTime(totalSeconds: number): string {
  const normalized = Math.max(0, Math.floor(totalSeconds))
  const hours = Math.floor(normalized / 3600)
  const minutes = Math.floor((normalized % 3600) / 60)
  const seconds = normalized % 60
  if (hours > 0) {
    return [hours, minutes, seconds].map((value, index) => (index === 0 ? value.toString() : value.toString().padStart(2, '0'))).join(':')
  }
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

function handleLoadedMetadata() {
  duration.value = videoRef.value?.duration || 0
}

function handleTimeUpdate() {
  currentTime.value = videoRef.value?.currentTime || 0
}

async function handlePlay() {
  if (!work.value || !videoRef.value) return
  await createPlaybackEvent(work.value.id, {
    event_type: 'play',
    to_seconds: videoRef.value.currentTime,
    duration_seconds: videoRef.value.duration || undefined,
  }).catch(() => undefined)
}

async function jumpToChapter(seconds: number) {
  if (!videoRef.value || !work.value) return
  const fromSeconds = videoRef.value.currentTime
  videoRef.value.currentTime = seconds
  currentTime.value = seconds
  await createPlaybackEvent(work.value.id, {
    event_type: 'seek',
    from_seconds: fromSeconds,
    to_seconds: seconds,
    duration_seconds: videoRef.value.duration || undefined,
  }).catch(() => undefined)
}

async function handleSeekInput(event: Event) {
  const nextTime = Number((event.target as HTMLInputElement).value)
  await jumpToChapter(nextTime)
}

function handleTimelineHover(event: MouseEvent) {
  const element = event.currentTarget as HTMLElement | null
  if (!element || !duration.value) return
  const rect = element.getBoundingClientRect()
  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width))
  const timeSeconds = ratio * duration.value
  preview.value = {
    visible: true,
    leftPercent: ratio * 100,
    timeSeconds,
    thumbnail: findNearestThumbnail(timeSeconds),
  }
}

function hidePreview() {
  preview.value.visible = false
}

function findNearestThumbnail(timeSeconds: number): HoverThumbnail | null {
  const items = playerMetadata.value.hover_thumbnails.items
  if (!items.length) return null
  return items.reduce((closest, item) => {
    if (!closest) return item
    return Math.abs(item.time_seconds - timeSeconds) < Math.abs(closest.time_seconds - timeSeconds) ? item : closest
  }, items[0])
}

onMounted(loadPage)
</script>

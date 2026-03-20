<template>
  <section v-if="work" class="page reader-page" :data-direction="direction" :dir="direction">
    <header class="page__header">
      <div>
        <p class="eyebrow">图片阅读器</p>
        <h2>{{ work.title }}</h2>
        <p>
          支持长滚动 / 单页分页、LTR / RTL，以及自动进度恢复与同步。
        </p>
      </div>
      <div class="stack reader-page__status">
        <span>第 {{ currentIndex + 1 }} / {{ imageFiles.length }} 页</span>
        <span>{{ saveStatus }}</span>
      </div>
    </header>

    <section class="panel stack reader-toolbar">
      <div class="filters">
        <label class="stack">
          <span>阅读模式</span>
          <select v-model="mode" data-testid="mode-select">
            <option value="scroll">长滚动</option>
            <option value="paged">单页分页</option>
          </select>
        </label>
        <label class="stack">
          <span>翻页方向</span>
          <select v-model="direction" data-testid="direction-select">
            <option value="ltr">LTR</option>
            <option value="rtl">RTL</option>
          </select>
        </label>
      </div>
      <div class="actions">
        <button @click="goToPage('prev')">{{ direction === 'rtl' ? '下一页' : '上一页' }}</button>
        <button @click="goToPage('next')">{{ direction === 'rtl' ? '上一页' : '下一页' }}</button>
      </div>
    </section>

    <section class="reader-layout">
      <aside class="panel reader-thumbs">
        <h3>缩略导航</h3>
        <div class="reader-thumbs__list" :class="`reader-thumbs__list--${direction}`">
          <button
            v-for="(file, index) in orderedFiles"
            :key="file.id"
            class="reader-thumbs__item"
            :class="{ 'reader-thumbs__item--active': index === activeOrderedIndex }"
            @click="jumpFromOrderedIndex(index)"
          >
            <img :src="file.content_url || file.path" :alt="file.name" loading="lazy" />
            <span>{{ file.order_index + 1 }}</span>
          </button>
        </div>
      </aside>

      <div class="panel reader-surface">
        <div
          v-if="mode === 'scroll'"
          ref="scrollContainer"
          class="reader-scroll"
          @scroll.passive="handleScroll"
        >
          <figure
            v-for="(file, index) in imageFiles"
            :key="file.id"
            :ref="(element) => setPageRef(element, index)"
            class="reader-scroll__page"
            :class="{ 'reader-scroll__page--active': index === currentIndex }"
          >
            <img :src="file.content_url || file.path" :alt="file.name" loading="lazy" />
            <figcaption>{{ index + 1 }} / {{ imageFiles.length }} · {{ file.name }}</figcaption>
          </figure>
        </div>

        <div v-else class="reader-paged" :class="`reader-paged--${direction}`">
          <button class="reader-paged__nav" @click="goToPage('prev')">
            {{ direction === 'rtl' ? '→' : '←' }}
          </button>
          <figure class="reader-paged__page">
            <img :src="currentFile?.content_url || currentFile?.path" :alt="currentFile?.name" />
            <figcaption>{{ currentIndex + 1 }} / {{ imageFiles.length }} · {{ currentFile?.name }}</figcaption>
          </figure>
          <button class="reader-paged__nav" @click="goToPage('next')">
            {{ direction === 'rtl' ? '←' : '→' }}
          </button>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchWork, trackWorkAccess } from '../api/client'
import type { Work } from '../types'

const route = useRoute()
const work = ref<Work | null>(null)
const mode = ref<ReaderMode>('scroll')
const direction = ref<ReaderDirection>('ltr')
const currentIndex = ref(0)
const scrollContainer = ref<HTMLElement | null>(null)
const pageRefs = ref<(HTMLElement | null)[]>([])
const saveStatus = ref('尚未同步')
const activeScrollRatio = ref(0)
const unloadHandler = () => {
  void flushProgress()
}
let saveTimer: ReturnType<typeof setTimeout> | null = null
let lastSavedSnapshot: ReaderSnapshot | null = null

const imageFiles = computed(() => (work.value?.files ?? []).filter((file) => file.kind === 'image'))
const orderedFiles = computed(() => (direction.value === 'rtl' ? [...imageFiles.value].reverse() : imageFiles.value))
const activeOrderedIndex = computed(() => {
  if (!imageFiles.value.length) return 0
  return direction.value === 'rtl' ? imageFiles.value.length - 1 - currentIndex.value : currentIndex.value
})
const currentFile = computed(() => imageFiles.value[currentIndex.value] ?? null)

function setPageRef(element: Element | null, index: number) {
  pageRefs.value[index] = element as HTMLElement | null
}

function buildSnapshot(): ReaderSnapshot | null {
  if (!work.value || !imageFiles.value.length) return null
  return snapshotForMode(mode.value, direction.value, work.value, currentIndex.value, activeScrollRatio.value)
}

async function syncProgress(snapshot: ReaderSnapshot) {
  if (!work.value) return
  const previousSnapshot = lastSavedSnapshot
  const success = await persistSnapshotWithRollback(
    snapshot,
    async (nextSnapshot) => {
      const saved = await saveReadingProgress(work.value!.id, nextSnapshot)
      lastSavedSnapshot = snapshotFromProgress(saved, work.value!)
      saveStatus.value = `已同步：第 ${saved.page} 页`
    },
    () => {
      lastSavedSnapshot = previousSnapshot
      saveStatus.value = '同步失败，保留本地进度，稍后重试'
    },
  )

  if (!success) {
    throw new Error('progress sync failed')
  }
}

function scheduleProgressSave() {
  const snapshot = buildSnapshot()
  if (!snapshot) return
  if (saveTimer) clearTimeout(saveTimer)
  saveStatus.value = '同步中...'
  saveTimer = setTimeout(() => {
    void syncProgress(snapshot).catch(() => undefined)
  }, 300)
}

async function flushProgress() {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  const snapshot = buildSnapshot()
  if (!snapshot) return
  try {
    await syncProgress(snapshot)
  } catch {
    // 已在 syncProgress 中回退并提示
  }
}

function jumpToIndex(index: number, options: { immediate?: boolean } = {}) {
  if (!work.value || !imageFiles.value.length) return
  currentIndex.value = Math.min(Math.max(index, 0), imageFiles.value.length - 1)
  activeScrollRatio.value = imageFiles.value.length > 1 ? currentIndex.value / (imageFiles.value.length - 1) : 0

  if (mode.value === 'scroll') {
    const target = pageRefs.value[currentIndex.value]
    if (target && scrollContainer.value) {
      scrollContainer.value.scrollTo({ top: target.offsetTop - 16, behavior: options.immediate ? 'auto' : 'smooth' })
    }
  }

  scheduleProgressSave()
}

function jumpFromOrderedIndex(index: number) {
  const actualIndex = direction.value === 'rtl' ? imageFiles.value.length - 1 - index : index
  jumpToIndex(actualIndex)
}

function goToPage(action: 'next' | 'prev') {
  if (!work.value) return
  jumpToIndex(nextIndex(currentIndex.value, action, direction.value, work.value))
}

function handleScroll() {
  const container = scrollContainer.value
  if (!container || !imageFiles.value.length) return

  const maxScroll = Math.max(container.scrollHeight - container.clientHeight, 1)
  activeScrollRatio.value = container.scrollTop / maxScroll

  let nearestIndex = 0
  let nearestDistance = Number.POSITIVE_INFINITY
  pageRefs.value.forEach((page, index) => {
    if (!page) return
    const distance = Math.abs(page.offsetTop - container.scrollTop)
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearestIndex = index
    }
  })
  currentIndex.value = nearestIndex
  scheduleProgressSave()
}

async function loadReader() {
  work.value = await fetchWork(route.params.id as string)
  if (work.value) {
    await trackWorkAccess(work.value.id, 'reader_open')
  }
})
</script>

<template>
  <section class="page" v-if="work">
    <header class="page__header">
      <div>
        <p class="eyebrow">作品详情</p>
        <h2>{{ work.title }}</h2>
        <p>{{ work.path }}</p>
      </div>
      <div class="actions">
        <RouterLink :to="work.type === 'comic' ? `/reader/${work.id}` : `/player/${work.id}`">
          {{ work.type === 'comic' ? '进入阅读器' : '进入播放器' }}
        </RouterLink>
        <button @click="handleGenerateThumbnails(false)">生成缩略图</button>
        <button @click="handleGenerateThumbnails(true)">强制重建缩略图</button>
        <button @click="handleExport">导出 sidecar</button>
        <button @click="handleImport">导入 sidecar</button>
      </div>
    </header>

    <section class="work-hero panel">
      <div class="work-hero__cover">
        <img v-if="work.cover_url" :src="work.cover_url" :alt="`${work.title} 当前封面`" />
        <div v-else class="reader__placeholder">暂无封面</div>
      </div>
      <div class="stack">
        <h3>当前封面</h3>
        <p v-if="work.current_cover">
          已选择 {{ work.type === 'comic' ? `第 ${work.current_cover.sort_no + 1} 页` : `${work.current_cover.ts_sec ?? 0}s` }}
        </p>
        <p v-else>当前仍使用扫描默认封面，建议生成缩略图后手动挑选。</p>
        <div class="chips">
          <span class="chip">{{ work.type === 'comic' ? '漫画封面候选' : '视频关键帧候选' }}</span>
          <span class="chip chip--muted">共 {{ work.thumbnails.length }} 张</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="row">
        <h3>封面候选</h3>
        <p v-if="statusMessage">{{ statusMessage }}</p>
      </div>
      <div v-if="work.thumbnails.length" class="thumbnail-grid">
        <button
          v-for="thumbnail in work.thumbnails"
          :key="thumbnail.id"
          class="thumbnail-card"
          :class="{ 'thumbnail-card--active': work.current_cover?.id === thumbnail.id }"
          @click="handleSelectCover(thumbnail.id)"
        >
          <img :src="thumbnail.thumbnail_url" :alt="`${work.title} thumbnail ${thumbnail.sort_no + 1}`" />
          <strong>{{ work.type === 'comic' ? `第 ${thumbnail.sort_no + 1} 页` : `${thumbnail.ts_sec ?? 0}s` }}</strong>
          <small>{{ thumbnail.type === 'cover' ? '封面页候选' : '关键帧候选' }}</small>
        </button>
      </div>
      <p v-else>尚未生成缩略图，可点击上方按钮显式触发。</p>
    </section>

    <section class="panel">
      <h3>标签</h3>
      <div class="chips">
        <span v-for="tag in work.tags" :key="tag.id" class="chip">{{ tag.name }}</span>
        <span v-if="!work.tags.length" class="chip chip--muted">暂无标签</span>
      </div>
    </section>

    <section class="panel">
      <h3>文件列表</h3>
      <ul>
        <li v-for="file in work.files" :key="file.id">
          {{ file.order_index + 1 }}. {{ file.name }}
        </li>
      </ul>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { exportSidecar, fetchWork, generateThumbnails, importSidecar, trackWorkAccess, updateWorkCover } from '../api/client'
import type { Work } from '../types'

const route = useRoute()
const work = ref<Work | null>(null)
const statusMessage = ref('')

async function loadWork() {
  work.value = await fetchWork(route.params.id as string)
}

async function handleGenerateThumbnails(force: boolean) {
  if (!work.value) return
  const result = await generateThumbnails(work.value.id, force)
  statusMessage.value = `已生成 ${result.generated} 张缩略图`
  await loadWork()
}

async function handleSelectCover(thumbnailId: number) {
  if (!work.value) return
  work.value = await updateWorkCover(work.value.id, thumbnailId)
  statusMessage.value = '封面已更新'
}

async function handleExport() {
  if (!work.value) return
  const result = await exportSidecar(work.value.id)
  statusMessage.value = `已导出到 ${result.sidecar_path}`
}

async function handleImport() {
  if (!work.value) return
  const result = await importSidecar(work.value.id)
  statusMessage.value = `已从 ${result.sidecar_path} 导入`
  await loadWork()
}

onMounted(async () => {
  await loadWork()
  if (work.value) {
    await trackWorkAccess(work.value.id, 'detail_open')
  }
})
</script>

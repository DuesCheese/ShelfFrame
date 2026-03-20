<template>
  <section class="page">
    <div v-if="errorMessage" class="notice notice--error">
      <strong>请求失败：</strong>{{ errorMessage }}
    </div>

    <template v-else-if="work">
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
          <button @click="handleExport">导出 sidecar</button>
          <button @click="handleImport">导入 sidecar</button>
        </div>
      </header>

      <section class="panel">
        <h3>标签</h3>
        <div class="chips">
          <span v-for="tag in work.tags" :key="tag.id" class="chip">{{ tag.name }}</span>
          <span v-if="!work.tags.length" class="chip chip--muted">暂无标签</span>
        </div>
        <p v-if="statusMessage" class="notice notice--success">{{ statusMessage }}</p>
      </section>

      <section class="panel">
        <h3>文件列表</h3>
        <ul>
          <li v-for="file in work.files" :key="file.id">
            {{ file.order_index + 1 }}. {{ file.name }}
          </li>
        </ul>
      </section>
    </template>
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
const errorMessage = ref('')

async function loadWork() {
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    work.value = await fetchWork(route.params.id as string)
  } catch (error) {
    work.value = null
    errorMessage.value = error instanceof Error ? error.message : '无法加载作品详情'
  }
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
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    const result = await exportSidecar(work.value.id)
    statusMessage.value = `已导出到 ${result.sidecar_path}`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '导出 sidecar 失败'
  }
}

async function handleImport() {
  if (!work.value) return
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    const result = await importSidecar(work.value.id)
    statusMessage.value = `已从 ${result.sidecar_path} 导入`
    await loadWork()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '导入 sidecar 失败'
  }
}

onMounted(async () => {
  await loadWork()
  if (work.value) {
    await trackWorkAccess(work.value.id, 'detail_open')
  }
})
</script>

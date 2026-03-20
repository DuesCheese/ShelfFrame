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
      <p v-if="statusMessage">{{ statusMessage }}</p>
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
import { exportSidecar, fetchWork, importSidecar } from '../api/client'
import type { Work } from '../types'

const route = useRoute()
const work = ref<Work | null>(null)
const statusMessage = ref('')

async function loadWork() {
  work.value = await fetchWork(route.params.id as string)
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

onMounted(loadWork)
</script>

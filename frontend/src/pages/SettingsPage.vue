<template>
  <section class="page">
    <header class="page__header">
      <div>
        <p class="eyebrow">Settings</p>
        <h2>系统设置</h2>
        <p>本阶段新增媒体目录持久化、标签管理，以及 sidecar 工作流入口。</p>
      </div>
    </header>

    <div class="settings-grid">
      <section class="panel">
        <h3>媒体目录</h3>
        <form class="stack" @submit.prevent="submitRoot">
          <input v-model="mediaRootInput" placeholder="/path/to/media" />
          <button type="submit">添加目录</button>
        </form>
        <ul class="stack">
          <li v-for="root in settings?.media_roots ?? []" :key="root.id" class="row">
            <span>{{ root.path }}</span>
            <button @click="removeRoot(root.id)">删除</button>
          </li>
        </ul>
      </section>

      <section class="panel">
        <h3>标签管理</h3>
        <form class="stack" @submit.prevent="submitTag">
          <input v-model="tagName" placeholder="标签名" />
          <input v-model="tagColor" placeholder="#2563eb（可选）" />
          <input v-model="tagGroup" placeholder="分组（可选）" />
          <button type="submit">新建标签</button>
        </form>
        <ul class="stack">
          <li v-for="tag in tags" :key="tag.id" class="row">
            <span>{{ tag.name }}</span>
            <button @click="removeTag(tag.id)">删除</button>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { createMediaRoot, createTag, deleteMediaRoot, deleteTag, fetchSettings, fetchTags } from '../api/client'
import type { Settings, Tag } from '../types'

const settings = ref<Settings | null>(null)
const tags = ref<Tag[]>([])
const mediaRootInput = ref('')
const tagName = ref('')
const tagColor = ref('')
const tagGroup = ref('')

async function loadSettings() {
  settings.value = await fetchSettings()
}

async function loadTags() {
  tags.value = await fetchTags()
}

async function submitRoot() {
  if (!mediaRootInput.value.trim()) return
  await createMediaRoot(mediaRootInput.value)
  mediaRootInput.value = ''
  await loadSettings()
}

async function removeRoot(id: number) {
  await deleteMediaRoot(id)
  await loadSettings()
}

async function submitTag() {
  if (!tagName.value.trim()) return
  await createTag({ name: tagName.value, color: tagColor.value || undefined, group_name: tagGroup.value || undefined })
  tagName.value = ''
  tagColor.value = ''
  tagGroup.value = ''
  await loadTags()
}

async function removeTag(id: number) {
  await deleteTag(id)
  await loadTags()
}

onMounted(async () => {
  await Promise.all([loadSettings(), loadTags()])
})
</script>

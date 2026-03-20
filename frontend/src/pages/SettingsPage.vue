<template>
  <section class="page">
    <header class="page__header">
      <div>
        <p class="eyebrow">Settings</p>
        <h2>系统设置</h2>
        <p>本阶段新增媒体目录持久化、标签管理，以及 sidecar 工作流入口。</p>
      </div>
    </header>

    <div v-if="errorMessage" class="notice notice--error">
      <strong>操作失败：</strong>{{ errorMessage }}
    </div>
    <p v-if="successMessage" class="notice notice--success">{{ successMessage }}</p>

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
const errorMessage = ref('')
const successMessage = ref('')

function resetMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}

async function loadSettings() {
  settings.value = await fetchSettings()
}

async function loadTags() {
  tags.value = await fetchTags()
}

async function submitRoot() {
  if (!mediaRootInput.value.trim()) return
  resetMessages()
  try {
    await createMediaRoot(mediaRootInput.value)
    mediaRootInput.value = ''
    successMessage.value = '媒体目录已保存'
    await loadSettings()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法添加媒体目录'
  }
}

async function removeRoot(id: number) {
  resetMessages()
  try {
    await deleteMediaRoot(id)
    successMessage.value = '媒体目录已删除'
    await loadSettings()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法删除媒体目录'
  }
}

async function submitTag() {
  if (!tagName.value.trim()) return
  resetMessages()
  try {
    await createTag({ name: tagName.value, color: tagColor.value || undefined, group_name: tagGroup.value || undefined })
    tagName.value = ''
    tagColor.value = ''
    tagGroup.value = ''
    successMessage.value = '标签已创建'
    await loadTags()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法创建标签'
  }
}

async function removeTag(id: number) {
  resetMessages()
  try {
    await deleteTag(id)
    successMessage.value = '标签已删除'
    await loadTags()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法删除标签'
  }
}

onMounted(async () => {
  resetMessages()
  try {
    await Promise.all([loadSettings(), loadTags()])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法加载设置页数据'
  }
})
</script>

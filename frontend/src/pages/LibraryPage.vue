<template>
  <section class="page">
    <header class="page__header">
      <div>
        <p class="eyebrow">Library</p>
        <h2>作品列表</h2>
      </div>
      <div class="filters">
        <input
          v-model.trim="searchQuery"
          class="filters__search"
          type="search"
          placeholder="搜索标题、简介、标签"
          @input="loadWorks"
        />
        <select v-model="selectedType" @change="loadWorks">
          <option value="">全部类型</option>
          <option value="comic">漫画</option>
          <option value="video">视频</option>
        </select>
        <select v-model="selectedTag" @change="loadWorks">
          <option value="">全部标签</option>
          <option v-for="tag in tags" :key="tag.id" :value="tag.name">{{ tag.name }}</option>
        </select>
      </div>
    </header>

    <div v-if="errorMessage" class="notice notice--error">
      <strong>加载失败：</strong>{{ errorMessage }}
    </div>

    <div class="grid" v-if="!errorMessage">
      <WorkCard v-for="work in works" :key="work.id" :work="work" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import WorkCard from '../components/WorkCard.vue'
import { fetchTags, fetchWorks } from '../api/client'
import type { Tag, Work } from '../types'

const works = ref<Work[]>([])
const tags = ref<Tag[]>([])
const selectedType = ref('')
const selectedTag = ref('')
const errorMessage = ref('')

async function loadWorks() {
  errorMessage.value = ''
  try {
    works.value = await fetchWorks({
      type: selectedType.value || undefined,
      tag: selectedTag.value || undefined,
    })
  } catch (error) {
    works.value = []
    errorMessage.value = error instanceof Error ? error.message : '无法加载作品列表'
  }
}

async function loadTags() {
  try {
    tags.value = await fetchTags()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法加载标签列表'
  }
}

onMounted(async () => {
  await Promise.all([loadWorks(), loadTags()])
})
</script>

<style scoped>
.filters__search {
  min-width: 16rem;
}
</style>

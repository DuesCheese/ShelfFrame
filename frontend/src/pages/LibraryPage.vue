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

    <div class="grid">
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
const searchQuery = ref('')

async function loadWorks() {
  works.value = await fetchWorks({
    type: selectedType.value || undefined,
    tag: selectedTag.value || undefined,
    q: searchQuery.value || undefined,
  })
}

onMounted(async () => {
  const [loadedTags] = await Promise.all([fetchTags(), loadWorks()])
  tags.value = loadedTags
})
</script>

<style scoped>
.filters__search {
  min-width: 16rem;
}
</style>

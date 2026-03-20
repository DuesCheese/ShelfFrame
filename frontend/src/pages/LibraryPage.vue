<template>
  <section class="page">
    <header class="page__header">
      <div>
        <p class="eyebrow">Library</p>
        <h2>作品列表</h2>
      </div>
      <div class="filters">
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

async function loadWorks() {
  works.value = await fetchWorks({
    type: selectedType.value || undefined,
    tag: selectedTag.value || undefined,
  })
}

onMounted(async () => {
  const [loadedWorks, loadedTags] = await Promise.all([fetchWorks(), fetchTags()])
  works.value = loadedWorks
  tags.value = loadedTags
})
</script>

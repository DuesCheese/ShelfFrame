<template>
  <section class="page">
    <header class="page__header">
      <div>
        <p class="eyebrow">Library</p>
        <h2>作品列表</h2>
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
import { fetchWorks } from '../api/client'
import type { Work } from '../types'

const works = ref<Work[]>([])

onMounted(async () => {
  works.value = await fetchWorks()
})
</script>

<template>
  <section class="page" v-if="work">
    <header class="page__header">
      <div>
        <p class="eyebrow">阅读器原型</p>
        <h2>{{ work.title }}</h2>
        <p>当前为长滚动阅读骨架，后续可扩展单页、RTL、章节导航与进度同步。</p>
      </div>
    </header>

    <div class="reader">
      <figure v-for="file in work.files" :key="file.id" class="reader__page">
        <div class="reader__placeholder">{{ file.name }}</div>
        <figcaption>{{ file.order_index + 1 }} / {{ work.files.length }}</figcaption>
      </figure>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchWork, trackWorkAccess } from '../api/client'
import type { Work } from '../types'

const route = useRoute()
const work = ref<Work | null>(null)

onMounted(async () => {
  work.value = await fetchWork(route.params.id as string)
  if (work.value) {
    await trackWorkAccess(work.value.id, 'reader_open')
  }
})
</script>

<template>
  <section class="page" v-if="work">
    <header class="page__header">
      <div>
        <p class="eyebrow">作品详情</p>
        <h2>{{ work.title }}</h2>
        <p>{{ work.path }}</p>
      </div>
      <RouterLink :to="work.type === 'comic' ? `/reader/${work.id}` : `/player/${work.id}`">
        {{ work.type === 'comic' ? '进入阅读器' : '进入播放器' }}
      </RouterLink>
    </header>

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
import { fetchWork } from '../api/client'
import type { Work } from '../types'

const route = useRoute()
const work = ref<Work | null>(null)

onMounted(async () => {
  work.value = await fetchWork(route.params.id as string)
})
</script>

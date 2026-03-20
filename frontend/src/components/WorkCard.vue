<template>
  <article class="card">
    <div class="card__cover">
      <img v-if="work.cover_url" :src="work.cover_url" :alt="`${work.title} cover`" />
      <span v-else>{{ work.type === 'comic' ? '漫画' : '视频' }}</span>
    </div>
    <div class="card__body">
      <h3>{{ work.title }}</h3>
      <p>{{ work.summary || '尚未补充简介，可在作品详情页中完善。' }}</p>
      <small>{{ work.files.length }} 个文件</small>
      <RouterLink :to="`/works/${work.id}`">查看详情</RouterLink>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { Work } from '../types'

defineProps<{ work: Work }>()
</script>

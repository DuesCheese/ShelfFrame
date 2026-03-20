<template>
  <section class="page" v-if="work">
    <header class="page__header">
      <div>
        <p class="eyebrow">播放器原型</p>
        <h2>{{ work.title }}</h2>
        <p>当前提供本地视频占位和章节/描述预留区域，后续接入原生 video 与预览图能力。</p>
      </div>
    </header>

    <div class="player-shell">
      <div class="player-shell__surface">
        <img v-if="work.current_cover" class="player-shell__preview" :src="work.current_cover.thumbnail_url" :alt="`${work.title} 预览图`" />
        <span v-else>{{ primaryFile?.name || '暂无视频文件' }}</span>
      </div>
      <aside class="panel">
        <h3>播放器扩展位</h3>
        <ul>
          <li>播放速度</li>
          <li>章节标签</li>
          <li>热度图</li>
          <li>hover thumbnail</li>
        </ul>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchWork, trackWorkAccess } from '../api/client'
import type { Work } from '../types'

const route = useRoute()
const work = ref<Work | null>(null)
const primaryFile = computed(() => work.value?.files[0])

onMounted(async () => {
  work.value = await fetchWork(route.params.id as string)
  if (work.value) {
    await trackWorkAccess(work.value.id, 'player_open')
  }
})
</script>

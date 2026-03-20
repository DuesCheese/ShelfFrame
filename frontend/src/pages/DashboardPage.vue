<template>
  <section class="page">
    <header class="page__header">
      <div>
        <p class="eyebrow">开发骨架</p>
        <h2>媒体库总览</h2>
        <p>这里聚合扫描状态、作品数量，以及阅读/播放入口。</p>
      </div>
      <button @click="scan">执行扫描</button>
    </header>

    <div class="stats">
      <div class="stat">
        <strong>{{ works.length }}</strong>
        <span>作品数</span>
      </div>
      <div class="stat">
        <strong>{{ comicCount }}</strong>
        <span>漫画</span>
      </div>
      <div class="stat">
        <strong>{{ videoCount }}</strong>
        <span>视频</span>
      </div>
      <div class="stat">
        <strong>{{ lastScan }}</strong>
        <span>上次扫描结果</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchWorks, triggerScan } from '../api/client'
import type { Work } from '../types'

const works = ref<Work[]>([])
const lastScan = ref('尚未执行')

const comicCount = computed(() => works.value.filter((work) => work.type === 'comic').length)
const videoCount = computed(() => works.value.filter((work) => work.type === 'video').length)

async function loadWorks() {
  works.value = await fetchWorks()
}

async function scan() {
  const result = await triggerScan()
  lastScan.value = `发现 ${result.discovered} / 新增 ${result.created} / 更新 ${result.updated}`
  await loadWorks()
}

onMounted(loadWorks)
</script>

<template>
  <section class="page">
    <header class="page__header">
      <div>
        <p class="eyebrow">开发骨架</p>
        <h2>媒体库总览</h2>
        <p>这里聚合扫描状态、媒体根目录数量，以及阅读/播放入口。</p>
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
        <strong>{{ rootCount }}</strong>
        <span>媒体目录</span>
      </div>
    </div>

    <section class="panel">
      <h3>最近扫描</h3>
      <p>{{ lastScan }}</p>
      <small v-if="roots.length">扫描目录：{{ roots.join('；') }}</small>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchSettings, fetchWorks, triggerScan } from '../api/client'
import type { Settings, Work } from '../types'

const works = ref<Work[]>([])
const roots = ref<string[]>([])
const lastScan = ref('尚未执行')
const settings = ref<Settings | null>(null)

const comicCount = computed(() => works.value.filter((work) => work.type === 'comic').length)
const videoCount = computed(() => works.value.filter((work) => work.type === 'video').length)
const rootCount = computed(() => settings.value?.media_roots.length ?? 0)

async function loadWorks() {
  works.value = await fetchWorks()
}

async function loadSettings() {
  settings.value = await fetchSettings()
}

async function scan() {
  const result = await triggerScan()
  roots.value = result.roots
  lastScan.value = `发现 ${result.discovered} / 新增 ${result.created} / 更新 ${result.updated} / 跳过 ${result.skipped}`
  await Promise.all([loadWorks(), loadSettings()])
}

onMounted(async () => {
  await Promise.all([loadWorks(), loadSettings()])
})
</script>

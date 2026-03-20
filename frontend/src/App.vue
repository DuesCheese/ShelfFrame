<template>
  <div class="shell">
    <aside class="sidebar">
      <h1>ShelfFrame</h1>
      <nav>
        <RouterLink to="/">概览</RouterLink>
        <RouterLink to="/library">媒体库</RouterLink>
        <RouterLink to="/settings">设置</RouterLink>
      </nav>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts"></script>

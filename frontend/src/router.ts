import { createRouter, createWebHistory } from 'vue-router'

import DashboardPage from './pages/DashboardPage.vue'
import LibraryPage from './pages/LibraryPage.vue'
import WorkDetailPage from './pages/WorkDetailPage.vue'
import ReaderPage from './pages/ReaderPage.vue'
import PlayerPage from './pages/PlayerPage.vue'
import SettingsPage from './pages/SettingsPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardPage },
    { path: '/library', component: LibraryPage },
    { path: '/works/:id', component: WorkDetailPage, props: true },
    { path: '/reader/:id', component: ReaderPage, props: true },
    { path: '/player/:id', component: PlayerPage, props: true },
    { path: '/settings', component: SettingsPage },
  ],
})

export default router

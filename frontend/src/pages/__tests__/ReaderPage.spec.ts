import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { route, fetchWork, fetchReadingProgress, saveReadingProgress } = vi.hoisted(() => ({
  route: { params: { id: '1' } },
  fetchWork: vi.fn(),
  fetchReadingProgress: vi.fn(),
  saveReadingProgress: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => route,
}))

vi.mock('../../api/client', () => ({
  fetchWork,
  fetchReadingProgress,
  saveReadingProgress,
}))

import ReaderPage from '../ReaderPage.vue'

const work = {
  id: 1,
  title: 'Demo Reader',
  path: '/tmp/demo',
  type: 'comic',
  created_at: '2026-03-20T00:00:00Z',
  updated_at: '2026-03-20T00:00:00Z',
  tags: [],
  files: [
    { id: 10, name: '001.jpg', path: '/tmp/demo/001.jpg', kind: 'image', size_bytes: 1, order_index: 0, content_url: '/api/works/1/files/10/content' },
    { id: 11, name: '002.jpg', path: '/tmp/demo/002.jpg', kind: 'image', size_bytes: 1, order_index: 1, content_url: '/api/works/1/files/11/content' },
    { id: 12, name: '003.jpg', path: '/tmp/demo/003.jpg', kind: 'image', size_bytes: 1, order_index: 2, content_url: '/api/works/1/files/12/content' },
  ],
  progress: null,
}

async function flushMounted(wrapper: ReturnType<typeof mount>) {
  await Promise.resolve()
  await nextTick()
  await nextTick()
  return wrapper
}

describe('ReaderPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    fetchWork.mockResolvedValue(structuredClone(work))
    fetchReadingProgress.mockResolvedValue(null)
    saveReadingProgress.mockResolvedValue({
      work_id: 1,
      chapter_key: null,
      file_index: 1,
      page: 2,
      position: 0.5,
      updated_at: '2026-03-20T00:01:00Z',
    })
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('切换到分页模式后显示单页视图', async () => {
    const wrapper = await flushMounted(mount(ReaderPage))
    await wrapper.get('[data-testid="mode-select"]').setValue('paged')
    await nextTick()

    expect(wrapper.find('.reader-paged').exists()).toBe(true)
    expect(wrapper.find('.reader-scroll').exists()).toBe(false)
  })

  it('RTL 模式下 next 会向更小页码翻动，并反转缩略导航', async () => {
    const wrapper = await flushMounted(mount(ReaderPage))
    await wrapper.get('[data-testid="mode-select"]').setValue('paged')
    await wrapper.get('[data-testid="direction-select"]').setValue('rtl')
    await nextTick()

    await wrapper.findAll('.reader-thumbs__item')[0].trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('第 3 / 3 页')

    await wrapper.findAll('.reader-paged__nav')[1].trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('第 2 / 3 页')
  })

  it('首次进入无进度时提示初始状态', async () => {
    const wrapper = await flushMounted(mount(ReaderPage))
    expect(fetchReadingProgress).toHaveBeenCalledWith('1')
    expect(wrapper.text()).toContain('首次进入，尚无进度')
    expect(wrapper.text()).toContain('第 1 / 3 页')
  })

  it('存在进度时恢复到对应页', async () => {
    fetchReadingProgress.mockResolvedValueOnce({
      work_id: 1,
      chapter_key: null,
      file_index: 2,
      page: 3,
      position: 1,
      updated_at: '2026-03-20T00:01:00Z',
    })

    const wrapper = await flushMounted(mount(ReaderPage))
    expect(wrapper.text()).toContain('已恢复：第 3 页')
    expect(wrapper.text()).toContain('第 3 / 3 页')
  })

  it('保存失败时回退并显示错误提示', async () => {
    saveReadingProgress.mockRejectedValue(new Error('boom'))
    const wrapper = await flushMounted(mount(ReaderPage))

    await wrapper.get('[data-testid="mode-select"]').setValue('paged')
    await wrapper.findAll('.reader-paged__nav')[1].trigger('click')
    await vi.runAllTimersAsync()
    await Promise.resolve()
    await Promise.resolve()
    await nextTick()

    expect(wrapper.text()).toContain('同步失败，保留本地进度，稍后重试')
  })
})

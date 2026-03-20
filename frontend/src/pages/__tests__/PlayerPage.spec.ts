import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PlayerPage from '../PlayerPage.vue'
import type { VideoPlayerMetadata, Work } from '../../types'

const mockRoute = {
  params: {
    id: '7',
  },
}

const apiMocks = vi.hoisted(() => ({
  fetchWork: vi.fn<() => Promise<Work>>(),
  fetchPlayerMetadata: vi.fn<() => Promise<VideoPlayerMetadata>>(),
  createPlaybackEvent: vi.fn<() => Promise<{ accepted: boolean }>>(),
  buildMediaFileUrl: vi.fn((fileId: number) => `/api/media/files/${fileId}`),
}))

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
}))

vi.mock('../../api/client', () => ({
  fetchWork: apiMocks.fetchWork,
  fetchPlayerMetadata: apiMocks.fetchPlayerMetadata,
  createPlaybackEvent: apiMocks.createPlaybackEvent,
  buildMediaFileUrl: apiMocks.buildMediaFileUrl,
}))

function createVideoWork(overrides: Partial<Work> = {}): Work {
  return {
    id: 7,
    title: 'Demo Video',
    path: '/media/demo.mp4',
    type: 'video',
    summary: 'Video summary',
    cover_path: null,
    created_at: '2026-03-20T00:00:00Z',
    updated_at: '2026-03-20T00:00:00Z',
    tags: [{ id: 1, name: '演示' }],
    files: [
      {
        id: 11,
        name: 'demo.mp4',
        path: '/media/demo.mp4',
        kind: 'video',
        size_bytes: 10485760,
        order_index: 0,
      },
    ],
    player_metadata: null,
    ...overrides,
  }
}

function createMetadata(overrides: Partial<VideoPlayerMetadata> = {}): VideoPlayerMetadata {
  return {
    source_url: '/api/media/files/11',
    chapters: [
      { label: '开场', start_seconds: 12, end_seconds: 48 },
      { label: '高潮', start_seconds: 70, end_seconds: 140 },
    ],
    hover_thumbnails: {
      status: 'pending',
      items: [],
    },
    heatmap: [{ start_seconds: 0, end_seconds: 30, intensity: 0.6, event_count: 2 }],
    ...overrides,
  }
}

describe('PlayerPage', () => {
  beforeEach(() => {
    apiMocks.fetchWork.mockReset()
    apiMocks.fetchPlayerMetadata.mockReset()
    apiMocks.createPlaybackEvent.mockReset()
    apiMocks.buildMediaFileUrl.mockClear()
    apiMocks.createPlaybackEvent.mockResolvedValue({ accepted: true })
  })

  it('renders empty-state when no video file exists', async () => {
    apiMocks.fetchWork.mockResolvedValue(createVideoWork({ files: [] }))
    apiMocks.fetchPlayerMetadata.mockResolvedValue(createMetadata({ source_url: null }))

    const wrapper = mount(PlayerPage)
    await flushPromises()

    expect(wrapper.text()).toContain('暂无视频文件')
  })

  it('jumps to chapter time when chapter button is clicked', async () => {
    apiMocks.fetchWork.mockResolvedValue(createVideoWork())
    apiMocks.fetchPlayerMetadata.mockResolvedValue(createMetadata())

    const wrapper = mount(PlayerPage)
    await flushPromises()

    const video = wrapper.get('video').element as HTMLVideoElement
    Object.defineProperty(video, 'currentTime', { value: 3, writable: true })
    Object.defineProperty(video, 'duration', { value: 180, writable: true })

    await wrapper.get('.chapter-list__button').trigger('click')

    expect(video.currentTime).toBe(12)
    expect(apiMocks.createPlaybackEvent).toHaveBeenCalledWith(7, expect.objectContaining({
      event_type: 'seek',
      from_seconds: 3,
      to_seconds: 12,
    }))
  })

  it('shows metadata region content', async () => {
    apiMocks.fetchWork.mockResolvedValue(createVideoWork())
    apiMocks.fetchPlayerMetadata.mockResolvedValue(createMetadata())

    const wrapper = mount(PlayerPage)
    await flushPromises()

    expect(wrapper.text()).toContain('媒体路径')
    expect(wrapper.text()).toContain('/media/demo.mp4')
    expect(wrapper.text()).toContain('文件大小')
    expect(wrapper.text()).toContain('10.0 MB')
    expect(wrapper.text()).toContain('演示')
  })

  it('shows metadata error fallback when player metadata request fails', async () => {
    apiMocks.fetchWork.mockResolvedValue(createVideoWork())
    apiMocks.fetchPlayerMetadata.mockRejectedValue(new Error('metadata failed'))

    const wrapper = mount(PlayerPage)
    await flushPromises()

    expect(wrapper.text()).toContain('metadata failed，已回退到基础信息展示。')
  })
})

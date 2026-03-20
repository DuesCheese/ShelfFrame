import type { ReaderDirection, ReaderMode, ReadingProgress, Work } from '../types'

export interface ReaderSnapshot {
  chapter_key?: string | null
  file_index: number
  page: number
  position: number
}

export function clampIndex(index: number, work: Work): number {
  return Math.min(Math.max(index, 0), Math.max(work.files.length - 1, 0))
}

export function createSnapshot(input: ReaderSnapshot, work: Work): ReaderSnapshot {
  const fileIndex = clampIndex(input.file_index, work)
  return {
    chapter_key: input.chapter_key ?? null,
    file_index: fileIndex,
    page: input.page > 0 ? input.page : fileIndex + 1,
    position: Math.min(Math.max(input.position, 0), 1),
  }
}

export function snapshotFromProgress(progress: ReadingProgress | null | undefined, work: Work): ReaderSnapshot {
  if (!progress) {
    return createSnapshot({ file_index: 0, page: 1, position: 0 }, work)
  }

  return createSnapshot(
    {
      chapter_key: progress.chapter_key,
      file_index: progress.file_index,
      page: progress.page,
      position: progress.position,
    },
    work,
  )
}

export function nextIndex(currentIndex: number, action: 'next' | 'prev', direction: ReaderDirection, work: Work): number {
  const delta = direction === 'rtl' ? -1 : 1
  const next = action === 'next' ? currentIndex + delta : currentIndex - delta
  return clampIndex(next, work)
}

export function snapshotForMode(
  mode: ReaderMode,
  direction: ReaderDirection,
  work: Work,
  currentIndex: number,
  scrollRatio: number,
): ReaderSnapshot {
  const index = clampIndex(currentIndex, work)
  return createSnapshot(
    {
      file_index: index,
      page: index + 1,
      position: mode === 'scroll' ? scrollRatio : direction === 'rtl' ? 1 - scrollRatio : scrollRatio,
    },
    work,
  )
}

export async function persistSnapshotWithRollback(
  snapshot: ReaderSnapshot,
  persist: (snapshot: ReaderSnapshot) => Promise<void>,
  onRollback: (snapshot: ReaderSnapshot) => void,
): Promise<boolean> {
  try {
    await persist(snapshot)
    return true
  } catch (error) {
    onRollback(snapshot)
    return false
  }
}

import type { ScanResult, Work } from '../types'

const jsonHeaders = {
  'Content-Type': 'application/json',
}

export async function fetchWorks(): Promise<Work[]> {
  const response = await fetch('/api/works')
  if (!response.ok) {
    throw new Error('Failed to load works')
  }
  return response.json()
}

export async function fetchWork(id: string | number): Promise<Work> {
  const response = await fetch(`/api/works/${id}`)
  if (!response.ok) {
    throw new Error('Failed to load work details')
  }
  return response.json()
}

export async function triggerScan(): Promise<ScanResult> {
  const response = await fetch('/api/scan', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    throw new Error('Failed to trigger scan')
  }
  return response.json()
}

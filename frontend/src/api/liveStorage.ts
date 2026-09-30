const STORAGE_KEY = 'liveSessionId'

export function readStoredLiveSessionId(): number | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === null) {
    return null
  }
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
}

export function storeLiveSessionId(id: number): void {
  localStorage.setItem(STORAGE_KEY, String(id))
}

export function clearStoredLiveSessionId(): void {
  localStorage.removeItem(STORAGE_KEY)
}

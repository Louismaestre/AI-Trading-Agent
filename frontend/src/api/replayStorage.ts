const STORAGE_KEY = 'replayId'

export function readStoredReplayId(): number | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === null) {
    return null
  }
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
}

export function storeReplayId(id: number): void {
  localStorage.setItem(STORAGE_KEY, String(id))
}

export function clearStoredReplayId(): void {
  localStorage.removeItem(STORAGE_KEY)
}

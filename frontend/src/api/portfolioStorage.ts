const STORAGE_KEY = 'portfolioId'

export function readStoredPortfolioId(): number | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === null) {
    return null
  }
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
}

export function storePortfolioId(id: number): void {
  localStorage.setItem(STORAGE_KEY, String(id))
}

export function clearStoredPortfolioId(): void {
  localStorage.removeItem(STORAGE_KEY)
}

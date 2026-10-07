export function formatPercent(fraction: string | number): string {
  return `${(Number(fraction) * 100).toFixed(2)} %`
}

export function formatRatio(value: string | number | null): string {
  if (value === null) {
    return '—'
  }
  return Number(value).toFixed(2)
}

export function formatEuro(value: string | number): string {
  return Number(value).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
}

export function performancePercent(totalValue: string, initialCapital: string): number {
  const initial = Number(initialCapital)
  if (initial === 0) {
    return 0
  }
  return ((Number(totalValue) - initial) / initial) * 100
}

export function positionPnl(quantity: number, averageCost: string, value: string): number {
  return Number(value) - quantity * Number(averageCost)
}

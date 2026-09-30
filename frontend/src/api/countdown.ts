const MINUTE = 60
const HOUR = 60 * MINUTE

export function remainingLabel(from: Date, to: Date): string {
  const seconds = Math.floor((to.getTime() - from.getTime()) / 1000)
  if (seconds <= 0) {
    return 'now'
  }
  const hours = Math.floor(seconds / HOUR)
  const minutes = Math.floor((seconds % HOUR) / MINUTE)
  const rest = seconds % MINUTE
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  if (minutes > 0) {
    return `${minutes}m ${rest}s`
  }
  return `${rest}s`
}

export function formatClock(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return date.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

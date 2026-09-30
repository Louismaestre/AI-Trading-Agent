import { formatEuro, formatPercent } from '../api/money'
import type { ReplayMetrics } from '../api/types'

export function MetricsTable({ metrics }: { metrics: ReplayMetrics }) {
  return (
    <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <Stat label="Total return" value={formatPercent(metrics.total_return)} />
      <Stat label="Max drawdown" value={formatPercent(metrics.max_drawdown)} />
      <Stat label="Orders" value={String(metrics.order_count)} />
      <Stat label="Fees" value={formatEuro(metrics.fees_paid)} />
      <Stat
        label="Hit rate"
        value={metrics.hit_rate === null ? '—' : formatPercent(metrics.hit_rate)}
      />
    </dl>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 text-lg font-semibold">{value}</dd>
    </div>
  )
}

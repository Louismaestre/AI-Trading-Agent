import { formatPercent, formatRatio } from '../api/money'
import type { ReplaySignificance, SharpeComparison } from '../api/types'

export function SignificanceTable({ scored }: { scored: ReplaySignificance }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <h2 className="text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Statistical significance
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Bootstrap 95 % Sharpe interval and paired tests vs the reference twins. Repeats above 1
        skip the LLM cache and use a slightly positive temperature.
      </p>
      <dl className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Stat
          label="Sharpe 95 % CI"
          value={
            scored.sharpe_ci === null
              ? '—'
              : `${formatRatio(scored.sharpe_ci.low)} – ${formatRatio(scored.sharpe_ci.high)}`
          }
        />
        <Stat label="vs hold" value={comparisonLabel(scored.vs_hold)} />
        <Stat label="vs SMA 20/50" value={comparisonLabel(scored.vs_sma)} />
        <Stat label="vs random" value={comparisonLabel(scored.vs_random)} />
        <Stat label="Repeat mean return" value={batchLabel(scored)} />
      </dl>
    </section>
  )
}

function comparisonLabel(compared: SharpeComparison | null): string {
  if (compared === null) {
    return '—'
  }
  const verdict = compared.significant ? 'significant' : 'not significant'
  return `p=${formatRatio(compared.p_value)} · ${verdict}`
}

function batchLabel(scored: ReplaySignificance): string {
  if (scored.batch === null) {
    return '—'
  }
  const mean = formatPercent(scored.batch.mean_return)
  if (scored.batch.std_return === null) {
    return `${mean} (n=${scored.batch.count})`
  }
  return `${mean} ± ${formatPercent(scored.batch.std_return)} (n=${scored.batch.count})`
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-medium">{value}</dd>
    </div>
  )
}

import { useHealth } from '../api/client'
import type { Health } from '../api/types'

export function HomePage() {
  const { data: health, error, isPending } = useHealth()

  return (
    <main className="mx-auto max-w-lg px-6 py-16 font-sans text-slate-800">
      <h1 className="text-2xl font-semibold tracking-tight">AI Trading Agent</h1>
      <p className="mt-2 text-sm text-slate-500">Backend health check</p>
      {error ? <p className="mt-8 text-sm text-red-700">{error.message}</p> : null}
      {health ? <HealthCard health={health} /> : null}
      {isPending ? <p className="mt-8 text-sm text-slate-500">Loading…</p> : null}
    </main>
  )
}

function HealthCard({ health }: { health: Health }) {
  return (
    <dl className="mt-8 divide-y divide-slate-200 rounded-lg border border-slate-200">
      <Row label="API" value={health.status} />
      <Row label="Environment" value={health.environment} />
      <Row label="Database" value={health.database} />
    </dl>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  const ok = value === 'ok'
  return (
    <div className="flex items-center justify-between px-4 py-3 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className={ok ? 'font-medium text-emerald-700' : 'font-medium'}>{value}</dd>
    </div>
  )
}

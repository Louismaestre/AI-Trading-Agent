import { useEffect, useState } from 'react'

import { barsToCandles, walkForwardRange } from '../api/chart'
import { usePrices } from '../api/client'
import { barsToIndexedEquity, equityToLine } from '../api/liveChart'
import { useReplay, useReplayDecisions, useReplayEquity, useReplayMetrics } from '../api/replay'
import { clearStoredReplayId, readStoredReplayId, storeReplayId } from '../api/replayStorage'
import type { Replay } from '../api/types'
import { CandlestickChart } from '../components/CandlestickChart'
import { DecisionFeed } from '../components/DecisionFeed'
import { EquityChart } from '../components/EquityChart'
import { MetricsTable } from '../components/MetricsTable'
import { StartReplayForm } from '../components/StartReplayForm'

export function ReplayPage() {
  const [replayId, setReplayId] = useState<number | null>(readStoredReplayId)
  const replay = useReplay(replayId)
  const lost = Boolean(replay.error?.message.startsWith('404'))
  const activeId = replayId !== null && !lost ? replayId : null

  useEffect(() => {
    if (lost) {
      clearStoredReplayId()
    }
  }, [lost])

  const range = walkForwardRange()
  const contextPrices = usePrices('^FCHI', range.contextStart, range.contextEnd)

  if (activeId === null) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <h1 className="text-xl font-semibold tracking-tight">Replay</h1>
        <p className="mt-2 text-sm text-slate-500">
          Walk-forward: {range.contextYear} is context (the model sees that completed year vs the
          CAC 40). {range.testYear} is the test — prices after <code>as_of</code> stay hidden.
          Default range is {range.testYear} year-to-date. Weekly is faster for a full year.
        </p>
        <StartReplayForm
          onStarted={(id) => {
            storeReplayId(id)
            setReplayId(id)
          }}
        />
        <section className="mt-8 rounded-lg border border-slate-200 bg-white">
          <h2 className="px-4 pt-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
            CAC 40 · {range.contextYear} (context)
          </h2>
          {contextPrices.error ? (
            <p className="px-4 py-8 text-sm text-red-700">{contextPrices.error.message}</p>
          ) : contextPrices.data ? (
            <CandlestickChart candles={barsToCandles(contextPrices.data)} />
          ) : (
            <p className="px-4 py-8 text-sm text-slate-500">Loading CAC 40 {range.contextYear}…</p>
          )}
        </section>
      </main>
    )
  }

  return (
    <ReplayView
      replayId={activeId}
      onReset={() => {
        clearStoredReplayId()
        setReplayId(null)
      }}
    />
  )
}

function ReplayView({ replayId, onReset }: { replayId: number; onReset: () => void }) {
  const replay = useReplay(replayId)
  const agentsEquity = useReplayEquity(replayId)
  const holdId = replay.data?.benchmark_replay_id ?? null
  const holdEquity = useReplayEquity(holdId)
  const decisions = useReplayDecisions(replayId)
  const metrics = useReplayMetrics(replayId)
  const row = replay.data
  const indexPrices = usePrices('^FCHI', row?.start_date ?? '', row?.end_date ?? '')
  const firstEquity = Number(agentsEquity.data?.[0]?.total_value ?? '100000')

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Replay</h1>
          {row ? <p className="mt-2 text-sm text-slate-500">{statusLine(row)}</p> : null}
        </div>
        <button
          type="button"
          onClick={onReset}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
        >
          New replay
        </button>
      </header>

      {row ? <ProgressBar done={row.days_done} total={row.days_total} /> : null}
      {row?.error_message ? <p className="text-sm text-red-700">{row.error_message}</p> : null}
      {replay.error ? <p className="text-sm text-red-700">{replay.error.message}</p> : null}

      {metrics.data ? <MetricsTable metrics={metrics.data} /> : null}

      <section className="rounded-lg border border-slate-200 bg-white">
        <h2 className="px-4 pt-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
          Equity · agents vs buy and hold vs CAC 40
        </h2>
        <p className="px-4 pt-1 text-xs text-slate-500">
          Black agents · grey equal-weight hold · blue CAC 40 (same window, scaled to starting cash)
        </p>
        <EquityChart
          agents={equityToLine(agentsEquity.data ?? [])}
          benchmark={equityToLine(holdEquity.data ?? [])}
          index={barsToIndexedEquity(indexPrices.data ?? [], firstEquity)}
        />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
          Decisions
        </h2>
        {decisions.error ? (
          <p className="text-sm text-red-700">{decisions.error.message}</p>
        ) : decisions.data ? (
          <DecisionFeed decisions={decisions.data} orders={[]} />
        ) : (
          <p className="text-sm text-slate-500">Loading decisions…</p>
        )}
      </section>
    </main>
  )
}

function statusLine(row: Replay): string {
  const window = `${row.start_date} → ${row.end_date} · ${row.decision_frequency}`
  if (row.current_date) {
    return `${row.status} · ${window} · last day ${row.current_date}`
  }
  return `${row.status} · ${window}`
}

function ProgressBar({ done, total }: { done: number; total: number }) {
  const percent = total === 0 ? 0 : Math.round((done / total) * 100)
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-500">
        <span>Progress</span>
        <span>
          {done} / {total} days
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded bg-slate-200">
        <div className="h-full bg-slate-900" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

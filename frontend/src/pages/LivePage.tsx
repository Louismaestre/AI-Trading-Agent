import { useEffect, useState } from 'react'

import { useInstruments } from '../api/client'
import { formatEuro } from '../api/money'
import { equityToLine, intradayStartIso, intradayToCandles, orderMarkers } from '../api/liveChart'
import {
  useLiveControl,
  useLiveDecisions,
  useLiveEquity,
  useLiveSession,
  useIntraday,
  useLiveOrders,
  useMarketStatus,
} from '../api/live'
import {
  clearStoredLiveSessionId,
  readStoredLiveSessionId,
  storeLiveSessionId,
} from '../api/liveStorage'
import { DecisionFeed } from '../components/DecisionFeed'
import { EquityChart } from '../components/EquityChart'
import { InstrumentList } from '../components/InstrumentList'
import { IntradayChart } from '../components/IntradayChart'
import { MarketClock } from '../components/MarketClock'
import { StartLiveForm } from '../components/StartLiveForm'

const DEFAULT_TICKER = 'MC.PA'

export function LivePage() {
  const [sessionId, setSessionId] = useState<number | null>(readStoredLiveSessionId)
  const [ticker, setTicker] = useState(DEFAULT_TICKER)
  const market = useMarketStatus()
  const session = useLiveSession(sessionId)
  const lost = Boolean(session.error?.message.startsWith('404'))
  const activeId = sessionId !== null && !lost ? sessionId : null

  useEffect(() => {
    if (lost) {
      clearStoredLiveSessionId()
    }
  }, [lost])

  if (activeId === null) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <h1 className="text-xl font-semibold tracking-tight">Live</h1>
        <p className="mt-2 text-sm text-slate-500">
          Start a session: agents trade during market hours, compared to an equal-weight buy-and-hold.
        </p>
        {market.data ? (
          <div className="mt-4">
            <MarketClock market={market.data} nextCycleAt={null} sessionStatus={null} />
          </div>
        ) : null}
        <StartLiveForm
          onStarted={(id) => {
            storeLiveSessionId(id)
            setSessionId(id)
          }}
        />
      </main>
    )
  }

  return (
    <LiveSessionView
      sessionId={activeId}
      ticker={ticker}
      onTicker={setTicker}
      onReset={() => {
        clearStoredLiveSessionId()
        setSessionId(null)
      }}
    />
  )
}

function LiveSessionView({
  sessionId,
  ticker,
  onTicker,
  onReset,
}: {
  sessionId: number
  ticker: string
  onTicker: (ticker: string) => void
  onReset: () => void
}) {
  const market = useMarketStatus()
  const session = useLiveSession(sessionId)
  const agentsEquity = useLiveEquity(sessionId)
  const benchmarkId = session.data?.benchmark_session_id ?? null
  const holdEquity = useLiveEquity(benchmarkId)
  const holdSession = useLiveSession(benchmarkId)
  const decisions = useLiveDecisions(sessionId)
  const orders = useLiveOrders(session.data?.portfolio_id ?? null)
  const instruments = useInstruments()
  const start = market.data ? intradayStartIso(market.data.now) : null
  const bars = useIntraday(ticker, start)
  const controls = useLiveControl(sessionId)
  const busy = controls.pause.isPending || controls.resume.isPending || controls.stop.isPending
  const status = session.data?.status
  const tradable = instruments.data?.filter((item) => !item.ticker.startsWith('^')) ?? []

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Live</h1>
          {market.data ? (
            <div className="mt-2">
              <MarketClock
                market={market.data}
                nextCycleAt={session.data?.next_cycle_at ?? null}
                sessionStatus={status ?? null}
              />
            </div>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {status === 'RUNNING' ? (
            <button type="button" className={buttonClass} disabled={busy} onClick={() => controls.pause.mutate()}>
              Pause
            </button>
          ) : null}
          {status === 'PAUSED' ? (
            <button type="button" className={buttonClass} disabled={busy} onClick={() => controls.resume.mutate()}>
              Resume
            </button>
          ) : null}
          {status === 'RUNNING' || status === 'PAUSED' ? (
            <button type="button" className={buttonClass} disabled={busy} onClick={() => controls.stop.mutate()}>
              Stop
            </button>
          ) : null}
          {status === 'STOPPED' ? (
            <button type="button" className={buttonClass} onClick={onReset}>
              New session
            </button>
          ) : null}
        </div>
      </header>

      {session.error ? <p className="text-sm text-red-700">{session.error.message}</p> : null}
      {session.data ? (
        <dl className="grid gap-4 sm:grid-cols-3">
          <Stat label="Agents" value={formatEuro(session.data.total_value)} />
          <Stat label="Cash" value={formatEuro(session.data.cash)} />
          <Stat
            label="Buy and hold"
            value={holdSession.data ? formatEuro(holdSession.data.total_value) : '—'}
          />
        </dl>
      ) : (
        <p className="text-sm text-slate-500">Loading session…</p>
      )}

      <section className="rounded-lg border border-slate-200 bg-white">
        <h2 className="px-4 pt-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
          Equity · agents vs buy and hold
        </h2>
        <EquityChart
          agents={equityToLine(agentsEquity.data ?? [])}
          benchmark={equityToLine(holdEquity.data ?? [])}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[16rem_1fr]">
        <aside className="overflow-y-auto rounded-lg border border-slate-200 bg-white">
          <h2 className="px-4 py-3 text-xs font-semibold tracking-wide text-slate-500 uppercase">
            Universe
          </h2>
          {tradable.length > 0 ? (
            <InstrumentList instruments={tradable} selected={ticker} onSelect={onTicker} />
          ) : (
            <p className="px-4 pb-3 text-sm text-slate-500">Loading…</p>
          )}
        </aside>
        <div className="rounded-lg border border-slate-200 bg-white">
          <h2 className="px-4 pt-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
            {ticker} · 5-minute bars
          </h2>
          <IntradayChart
            candles={intradayToCandles(bars.data ?? [])}
            markers={orderMarkers(orders.data ?? [], ticker)}
          />
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
          Decisions
        </h2>
        {decisions.data ? (
          <DecisionFeed decisions={decisions.data} orders={orders.data ?? []} />
        ) : (
          <p className="text-sm text-slate-500">Loading…</p>
        )}
      </section>
    </main>
  )
}

const buttonClass =
  'rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:bg-slate-300'

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 text-lg font-semibold">{value}</dd>
    </div>
  )
}

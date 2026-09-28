import { useState } from 'react'

import { barsToCandles, defaultPriceRange, lastDayChange } from '../api/chart'
import { useInstruments, usePrices } from '../api/client'
import { CandlestickChart } from '../components/CandlestickChart'
import { InstrumentList } from '../components/InstrumentList'

const DEFAULT_TICKER = 'MC.PA'

export function MarketPage() {
  const [ticker, setTicker] = useState(DEFAULT_TICKER)
  const range = defaultPriceRange()
  const instruments = useInstruments()
  const prices = usePrices(ticker, range.start, range.end)
  const selected = instruments.data?.find((item) => item.ticker === ticker)
  const change = prices.data ? lastDayChange(prices.data) : null
  const up = change !== null && change.change >= 0

  return (
    <main className="mx-auto flex min-h-[calc(100svh-3.5rem)] max-w-6xl">
      <aside className="w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white">
        <h2 className="px-4 py-3 text-xs font-semibold tracking-wide text-slate-500 uppercase">
          Universe
        </h2>
        {instruments.error ? (
          <p className="px-4 text-sm text-red-700">{instruments.error.message}</p>
        ) : null}
        {instruments.data ? (
          <InstrumentList instruments={instruments.data} selected={ticker} onSelect={setTicker} />
        ) : (
          <p className="px-4 py-3 text-sm text-slate-500">Loading…</p>
        )}
      </aside>
      <section className="min-w-0 flex-1 bg-white px-6 py-5">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{selected?.name ?? ticker}</h1>
            <p className="text-sm text-slate-500">{ticker}</p>
          </div>
          {change ? (
            <p className={`text-sm font-medium ${up ? 'text-emerald-700' : 'text-red-700'}`}>
              {change.close.toFixed(2)} €{' '}
              <span>
                {up ? '+' : ''}
                {change.change.toFixed(2)} ({up ? '+' : ''}
                {change.percent.toFixed(2)}%)
              </span>
            </p>
          ) : null}
        </div>
        {prices.error ? <p className="text-sm text-red-700">{prices.error.message}</p> : null}
        {prices.isPending ? <p className="text-sm text-slate-500">Loading prices…</p> : null}
        {prices.data ? <CandlestickChart candles={barsToCandles(prices.data)} /> : null}
      </section>
    </main>
  )
}

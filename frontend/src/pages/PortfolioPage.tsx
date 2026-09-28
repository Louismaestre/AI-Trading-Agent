import { useState } from 'react'

import { useCreatePortfolio, useInstruments, useOrders, usePlaceOrder, usePortfolio } from '../api/client'
import { formatEuro, performancePercent } from '../api/money'
import { readStoredPortfolioId, storePortfolioId } from '../api/portfolioStorage'
import type { PlaceOrderBody } from '../api/types'
import { OrderForm } from '../components/OrderForm'
import { OrdersTable } from '../components/OrdersTable'
import { PositionsTable } from '../components/PositionsTable'

export function PortfolioPage() {
  const [portfolioId, setPortfolioId] = useState<number | null>(readStoredPortfolioId)
  const create = useCreatePortfolio()
  const portfolio = usePortfolio(portfolioId)
  const lost = Boolean(portfolio.error?.message.startsWith('404'))
  const orders = useOrders(lost ? null : portfolioId)
  const instruments = useInstruments()
  const place = usePlaceOrder(portfolioId ?? 0)

  async function handleCreate() {
    const created = await create.mutateAsync()
    storePortfolioId(created.id)
    setPortfolioId(created.id)
  }

  function handleOrder(body: PlaceOrderBody) {
    if (portfolioId === null) {
      return
    }
    place.mutate(body)
  }

  if (portfolioId === null || lost) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <h1 className="text-xl font-semibold tracking-tight">Portfolio</h1>
        <p className="mt-2 text-sm text-slate-500">Create a simulated portfolio to place manual orders.</p>
        <button
          type="button"
          onClick={() => void handleCreate()}
          disabled={create.isPending}
          className="mt-6 rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
        >
          {create.isPending ? 'Creating…' : 'Create demo portfolio'}
        </button>
        {create.error ? <p className="mt-3 text-sm text-red-700">{create.error.message}</p> : null}
      </main>
    )
  }

  const snapshot = portfolio.data
  const perf = snapshot ? performancePercent(snapshot.total_value, snapshot.initial_capital) : 0

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">{snapshot?.name ?? 'Portfolio'}</h1>
        {snapshot ? (
          <dl className="mt-4 grid gap-4 sm:grid-cols-3">
            <Stat label="Total value" value={formatEuro(snapshot.total_value)} />
            <Stat label="Cash" value={formatEuro(snapshot.cash)} />
            <Stat
              label="Performance"
              value={`${perf >= 0 ? '+' : ''}${perf.toFixed(2)} %`}
              tone={perf >= 0 ? 'up' : 'down'}
            />
          </dl>
        ) : (
          <p className="mt-4 text-sm text-slate-500">Loading…</p>
        )}
      </header>

      <section>
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">New order</h2>
        {instruments.data ? (
          <OrderForm
            instruments={instruments.data}
            isPending={place.isPending}
            error={place.error?.message ?? null}
            onSubmit={handleOrder}
          />
        ) : (
          <p className="text-sm text-slate-500">Loading instruments…</p>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">Positions</h2>
        {snapshot ? <PositionsTable positions={snapshot.positions} /> : null}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">Orders</h2>
        {orders.data ? <OrdersTable orders={orders.data} /> : <p className="text-sm text-slate-500">Loading…</p>}
      </section>
    </main>
  )
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'up' | 'down' }) {
  const color =
    tone === 'up' ? 'text-emerald-700' : tone === 'down' ? 'text-red-700' : 'text-slate-900'
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className={`mt-1 text-lg font-semibold ${color}`}>{value}</dd>
    </div>
  )
}

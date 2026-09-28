import { type FormEvent, useState } from 'react'

import type { Instrument, OrderSide, PlaceOrderBody } from '../api/types'
import { parseQuantity } from './parseQuantity'

type Props = {
  instruments: Instrument[]
  isPending: boolean
  error: string | null
  onSubmit: (body: PlaceOrderBody) => void
}

export function OrderForm({ instruments, isPending, error, onSubmit }: Props) {
  const [ticker, setTicker] = useState(tradable(instruments)[0]?.ticker ?? '')
  const [side, setSide] = useState<OrderSide>('BUY')
  const [quantity, setQuantity] = useState('1')
  const parsed = parseQuantity(quantity)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (parsed === null || ticker === '') {
      return
    }
    onSubmit({ ticker, side, quantity: parsed })
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-4">
      <label className="text-sm">
        <span className="mb-1 block text-slate-500">Instrument</span>
        <select
          value={ticker}
          onChange={(event) => setTicker(event.target.value)}
          className="w-full rounded border border-slate-300 px-2 py-1.5"
        >
          {tradable(instruments).map((instrument) => (
            <option key={instrument.ticker} value={instrument.ticker}>
              {instrument.ticker} — {instrument.name}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-slate-500">Side</span>
        <select
          value={side}
          onChange={(event) => setSide(event.target.value as OrderSide)}
          className="w-full rounded border border-slate-300 px-2 py-1.5"
        >
          <option value="BUY">Buy</option>
          <option value="SELL">Sell</option>
        </select>
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-slate-500">Quantity</span>
        <input
          type="number"
          min={1}
          step={1}
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
          className="w-full rounded border border-slate-300 px-2 py-1.5"
        />
      </label>
      <div className="flex items-end">
        <button
          type="submit"
          disabled={isPending || parsed === null || ticker === ''}
          className="w-full rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:bg-slate-300"
        >
          {isPending ? 'Sending…' : 'Place order'}
        </button>
      </div>
      {parsed === null ? <p className="text-sm text-red-700 sm:col-span-4">Quantity must be a positive integer.</p> : null}
      {error ? <p className="text-sm text-red-700 sm:col-span-4">{error}</p> : null}
    </form>
  )
}

function tradable(instruments: Instrument[]): Instrument[] {
  return instruments.filter((instrument) => !instrument.ticker.startsWith('^'))
}

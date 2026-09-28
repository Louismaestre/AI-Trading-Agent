import type { Instrument } from '../api/types'

type Props = {
  instruments: Instrument[]
  selected: string
  onSelect: (ticker: string) => void
}

export function InstrumentList({ instruments, selected, onSelect }: Props) {
  return (
    <ul className="divide-y divide-slate-200">
      {instruments.map((instrument) => {
        const active = instrument.ticker === selected
        return (
          <li key={instrument.ticker}>
            <button
              type="button"
              onClick={() => onSelect(instrument.ticker)}
              className={`flex w-full flex-col items-start px-4 py-3 text-left text-sm ${
                active ? 'bg-slate-900 text-white' : 'hover:bg-slate-100'
              }`}
            >
              <span className="font-medium">{instrument.ticker}</span>
              <span className={active ? 'text-slate-300' : 'text-slate-500'}>{instrument.name}</span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

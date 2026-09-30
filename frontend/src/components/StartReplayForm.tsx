import { useState, type FormEvent } from 'react'

import { isoDate } from '../api/chart'
import { useStartReplay } from '../api/replay'

type Props = {
  onStarted: (replayId: number) => void
}

function defaultRange(): { start: string; end: string } {
  const end = new Date()
  const start = new Date()
  start.setMonth(end.getMonth() - 3)
  return { start: isoDate(start), end: isoDate(end) }
}

export function StartReplayForm({ onStarted }: Props) {
  const range = defaultRange()
  const start = useStartReplay()
  const [name, setName] = useState('Replay')
  const [capital, setCapital] = useState('100000')
  const [from, setFrom] = useState(range.start)
  const [to, setTo] = useState(range.end)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const replay = await start.mutateAsync({
      name,
      initial_capital: capital,
      start: from,
      end: to,
    })
    onStarted(replay.id)
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="mt-6 max-w-md space-y-4">
      <label className="block text-sm">
        <span className="text-slate-500">Name</span>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        <span className="text-slate-500">Capital (€)</span>
        <input
          value={capital}
          onChange={(event) => setCapital(event.target.value)}
          inputMode="decimal"
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        <span className="text-slate-500">Start</span>
        <input
          type="date"
          value={from}
          onChange={(event) => setFrom(event.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        <span className="text-slate-500">End</span>
        <input
          type="date"
          value={to}
          onChange={(event) => setTo(event.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        />
      </label>
      <button
        type="submit"
        disabled={start.isPending}
        className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
      >
        {start.isPending ? 'Starting…' : 'Start replay'}
      </button>
      {start.error ? <p className="text-sm text-red-700">{start.error.message}</p> : null}
    </form>
  )
}

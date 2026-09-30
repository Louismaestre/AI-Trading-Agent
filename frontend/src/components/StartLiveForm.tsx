import { useState, type FormEvent } from 'react'

import { useStartLiveSession } from '../api/live'

type Props = {
  onStarted: (sessionId: number) => void
}

export function StartLiveForm({ onStarted }: Props) {
  const start = useStartLiveSession()
  const [name, setName] = useState('Live')
  const [capital, setCapital] = useState('100000')
  const [interval, setInterval] = useState('15')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const session = await start.mutateAsync({
      name,
      initial_capital: capital,
      interval_minutes: Number(interval),
    })
    onStarted(session.id)
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
        <span className="text-slate-500">Interval (minutes)</span>
        <select
          value={interval}
          onChange={(event) => setInterval(event.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        >
          <option value="5">5</option>
          <option value="15">15</option>
          <option value="30">30</option>
        </select>
      </label>
      <button
        type="submit"
        disabled={start.isPending}
        className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
      >
        {start.isPending ? 'Starting…' : 'Start session'}
      </button>
      {start.error ? <p className="text-sm text-red-700">{start.error.message}</p> : null}
    </form>
  )
}

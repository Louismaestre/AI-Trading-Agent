import { useNavigate, useParams } from 'react-router-dom'

import { useDecision } from '../api/client'
import type { AgentDecisionDetail } from '../api/types'

export function DecisionPage() {
  const rawId = Number(useParams().decisionId)
  const id = Number.isFinite(rawId) && rawId > 0 ? rawId : null
  const query = useDecision(id)

  if (id === null) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-sm text-red-700">Unknown decision.</p>
      </main>
    )
  }

  if (query.error) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <BackLink />
        <p className="mt-4 text-sm text-red-700">{query.error.message}</p>
      </main>
    )
  }

  if (!query.data) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <BackLink />
        <p className="mt-4 text-sm text-slate-500">Loading decision…</p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-3xl space-y-8 px-6 py-10">
      <BackLink />
      <DecisionHeader decision={query.data} />
      <ReportsSection reports={query.data.reports} />
      <DebateSection debate={query.data.debate} />
      <RiskSection risk={query.data.risk} />
    </main>
  )
}

function BackLink() {
  const navigate = useNavigate()
  return (
    <button
      type="button"
      onClick={() => navigate(-1)}
      className="text-sm text-slate-500 hover:text-slate-800"
    >
      ← Back
    </button>
  )
}

export function DecisionHeader({ decision }: { decision: AgentDecisionDetail }) {
  return (
    <header>
      <p className="text-sm text-slate-500">
        {decision.as_of} · {decision.ticker}
      </p>
      <h1 className={`mt-1 text-2xl font-semibold tracking-tight ${actionTone(decision.action)}`}>
        {decision.action}
      </h1>
      <p className="mt-3 text-sm text-slate-600">{decision.rationale}</p>
      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <Stat label="Confidence" value={`${(decision.confidence * 100).toFixed(0)} %`} />
        <Stat label="Target weight" value={`${(decision.target_weight * 100).toFixed(1)} %`} />
        <Stat label="Model" value={decision.llm_model} />
      </dl>
    </header>
  )
}

export function ReportsSection({ reports }: { reports: AgentDecisionDetail['reports'] }) {
  const entries = Object.entries(reports)
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Specialist reports
      </h2>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">No specialist report on this decision.</p>
      ) : (
        <ul className="space-y-3">
          {entries.map(([name, report]) => (
            <li key={name} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
              <p className="text-sm font-medium text-slate-800">
                {name} · {report.stance} · {(report.confidence * 100).toFixed(0)} %
              </p>
              <p className="mt-1 text-sm text-slate-600">{report.rationale}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function DebateSection({ debate }: { debate: AgentDecisionDetail['debate'] }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">Debate</h2>
      {debate.length === 0 ? (
        <p className="text-sm text-slate-500">No debate on this decision.</p>
      ) : (
        <ol className="space-y-3">
          {debate.map((turn, index) => (
            <li key={`${turn.side}-${index}`} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
              <p className="text-sm font-medium text-slate-800">
                {turn.side} · {(turn.conviction * 100).toFixed(0)} %
              </p>
              <p className="mt-1 text-sm text-slate-600">{turn.argument}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export function RiskSection({ risk }: { risk: AgentDecisionDetail['risk'] }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">Risk</h2>
      {risk === null ? (
        <p className="text-sm text-slate-500">Risk manager was off for this run.</p>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-sm font-medium text-slate-800">
            {risk.approved ? 'Approved' : 'Refused'} · {risk.action} ·{' '}
            {(risk.target_weight * 100).toFixed(1)} %
          </p>
          {risk.reasons.length > 0 ? (
            <p className="mt-1 text-sm text-slate-600">{risk.reasons.join(' ')}</p>
          ) : null}
          {risk.triggered_rules.length > 0 ? (
            <p className="mt-2 text-xs text-slate-500">Rules: {risk.triggered_rules.join(', ')}</p>
          ) : null}
        </div>
      )}
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-slate-900">{value}</dd>
    </div>
  )
}

function actionTone(action: AgentDecisionDetail['action']): string {
  if (action === 'BUY') {
    return 'text-emerald-700'
  }
  if (action === 'SELL') {
    return 'text-red-700'
  }
  return 'text-slate-800'
}

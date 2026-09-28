import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Health' },
  { to: '/market', label: 'Market' },
  { to: '/portfolio', label: 'Portfolio' },
]

export function AppNav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-6">
        <span className="text-sm font-semibold tracking-tight">AI Trading Agent</span>
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/'}
            className={({ isActive }) =>
              `text-sm ${isActive ? 'font-medium text-slate-900' : 'text-slate-500 hover:text-slate-800'}`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </header>
  )
}

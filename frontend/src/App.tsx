import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AppNav } from './components/AppNav'
import { HomePage } from './pages/HomePage'
import { LivePage } from './pages/LivePage'
import { MarketPage } from './pages/MarketPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { ReplayPage } from './pages/ReplayPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-svh bg-slate-50 font-sans text-slate-800">
        <AppNav />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/live" element={<LivePage />} />
          <Route path="/replay" element={<ReplayPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

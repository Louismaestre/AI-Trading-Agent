import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AppNav } from './components/AppNav'
import { HomePage } from './pages/HomePage'
import { MarketPage } from './pages/MarketPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-svh bg-slate-50 font-sans text-slate-800">
        <AppNav />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/market" element={<MarketPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

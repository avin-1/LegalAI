import { useState, useEffect } from 'react'
import { Toaster } from 'sonner'
import { AnimatePresence } from 'framer-motion'
import Auth from './components/Auth'
import Dashboard from './Dashboard'
import './App.css'

export default function App() {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<string>('')
  const [isInitializing, setIsInitializing] = useState(true)

  useEffect(() => {
    const savedToken = localStorage.getItem('opaque_token')
    const savedUser = localStorage.getItem('username')
    const expiry = localStorage.getItem('token_expires_at')

    if (savedToken && savedUser && expiry) {
      if (new Date(expiry) > new Date()) {
        setToken(savedToken)
        setUser(savedUser)
      } else {
        localStorage.clear()
      }
    }
    setIsInitializing(false)
  }, [])

  const handleLogout = () => {
    localStorage.clear()
    setToken(null)
    setUser('')
  }

  if (isInitializing) return null

  return (
    <>
      <Toaster 
        position="top-center" 
        toastOptions={{ 
          style: { 
            background: 'rgba(30, 30, 30, 0.8)', 
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#fff',
            fontFamily: 'Outfit, sans-serif'
          } 
        }} 
      />
      
      <AnimatePresence mode="wait">
        {token ? (
          <Dashboard key="dashboard" token={token} username={user} onLogout={handleLogout} />
        ) : (
          <Auth key="auth" onLogin={(t, u) => { setToken(t); setUser(u) }} />
        )}
      </AnimatePresence>
    </>
  )
}

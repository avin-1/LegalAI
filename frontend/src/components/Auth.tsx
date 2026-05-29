import { useState, type FormEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Scale, Lock, User, ArrowRight, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

type Tab = 'login' | 'signup'

interface AuthResponse {
  token: string
  expires_at: string
}

interface AuthProps {
  onLogin: (token: string, username: string) => void
}

const GATEWAY_BASE = import.meta.env.VITE_GATEWAY_BASE || 'http://localhost:3000'

export default function Auth({ onLogin }: AuthProps) {
  const [tab, setTab] = useState<Tab>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!username || !password) {
      toast.error('Please fill in all fields')
      return
    }

    setLoading(true)
    const endpoint = tab === 'login'
      ? `${GATEWAY_BASE}/api/auth/login`
      : `${GATEWAY_BASE}/api/auth/signup`

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })

      const data = await res.json()

      if (!res.ok) {
        toast.error(data.error ?? 'Authentication failed.')
        setLoading(false)
        return
      }

      const { token, expires_at } = data as AuthResponse
      localStorage.setItem('opaque_token', token)
      localStorage.setItem('token_expires_at', expires_at)
      localStorage.setItem('username', username)
      
      toast.success(tab === 'login' ? 'Welcome back!' : 'Account created successfully!')
      
      // Delay slightly for animation
      setTimeout(() => {
        onLogin(token, username)
      }, 800)

    } catch {
      toast.error('Connection refused to API Gateway.')
      setLoading(false)
    }
  }

  return (
    <motion.div 
      className="page"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.5 }}
    >
      <motion.div 
        className="glass-panel" 
        style={{ width: '100%', maxWidth: '420px', padding: '40px' }}
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, type: 'spring', stiffness: 300, damping: 20 }}
      >
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1, rotate: 360 }}
            transition={{ type: 'spring', delay: 0.4, stiffness: 200, damping: 20 }}
            style={{ 
              width: '64px', height: '64px', 
              background: 'linear-gradient(135deg, var(--accent-base), var(--accent-hover))',
              borderRadius: '20px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 24px',
              boxShadow: '0 8px 32px var(--accent-glow)'
            }}
          >
            <Scale color="white" size={32} />
          </motion.div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '8px', letterSpacing: '-0.5px' }}>
            Legal<span style={{ color: 'var(--accent-hover)' }}>AI</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>Enterprise Intelligence Platform</p>
        </div>

        <div style={{ display: 'flex', marginBottom: '32px', position: 'relative', borderBottom: '1px solid var(--border-subtle)' }}>
          {(['login', 'signup'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                flex: 1,
                padding: '12px 0',
                background: 'none',
                border: 'none',
                color: tab === t ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: 500,
                cursor: 'pointer',
                position: 'relative'
              }}
            >
              {t === 'login' ? 'Sign In' : 'Create Account'}
              {tab === t && (
                <motion.div
                  layoutId="active-tab"
                  style={{
                    position: 'absolute',
                    bottom: -1,
                    left: 0,
                    right: 0,
                    height: '2px',
                    background: 'var(--accent-hover)',
                    borderRadius: '2px 2px 0 0'
                  }}
                />
              )}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ x: 10, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -10, opacity: 0 }}
              transition={{ duration: 0.2 }}
              style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}
            >
              <div style={{ position: 'relative' }}>
                <User size={20} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                <input
                  className="form-input"
                  style={{ paddingLeft: '48px' }}
                  type="text"
                  placeholder="Username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  disabled={loading}
                />
              </div>

              <div style={{ position: 'relative' }}>
                <Lock size={20} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                <input
                  className="form-input"
                  style={{ paddingLeft: '48px' }}
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
            </motion.div>
          </AnimatePresence>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ marginTop: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
          >
            {loading ? (
              <Loader2 className="animate-spin" size={20} style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <>
                {tab === 'login' ? 'Access Workspace' : 'Provision Account'}
                <ArrowRight size={18} />
              </>
            )}
          </motion.button>
        </form>
      </motion.div>
    </motion.div>
  )
}

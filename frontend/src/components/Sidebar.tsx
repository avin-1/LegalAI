import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Scale, LogOut, FileText, UploadCloud, CheckCircle2, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'

interface SidebarProps {
  username: string
  token: string
  onLogout: () => void
  activeDocument: string
  onDocumentChange: (docName: string) => void
}

const GATEWAY_BASE = import.meta.env.VITE_GATEWAY_BASE || 'http://localhost:3000'

export default function Sidebar({ username, token, onLogout, activeDocument, onDocumentChange }: SidebarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    const toastId = toast.loading('Processing document...')

    const formData = new FormData()
    formData.append('file', file)
    formData.append('userid', username)

    try {
      const res = await fetch(`${GATEWAY_BASE}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      })

      const data = await res.json()
      if (res.ok) {
        toast.success('Document indexed successfully', { id: toastId })
        onDocumentChange(file.name)
      } else {
        toast.error(data.error || 'Upload failed', { id: toastId })
      }
    } catch (err) {
      toast.error('Could not connect to document processing service', { id: toastId })
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <motion.aside 
      initial={{ x: -300 }}
      animate={{ x: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      style={{
        width: '320px',
        background: 'var(--bg-surface)',
        backdropFilter: 'var(--glass-blur)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 10
      }}
    >
      <div style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ 
          width: '40px', height: '40px', 
          background: 'linear-gradient(135deg, var(--accent-base), var(--accent-hover))',
          borderRadius: '12px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 12px var(--accent-glow)'
        }}>
          <Scale color="white" size={20} />
        </div>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>LegalAI Base</h2>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>Knowledge Graph</p>
        </div>
      </div>

      <div style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
        <h3 style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '16px', fontWeight: 600 }}>
          Knowledge Base
        </h3>
        
        <motion.div 
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => !uploading && fileInputRef.current?.click()}
          style={{
            border: '2px dashed var(--border-strong)',
            borderRadius: 'var(--radius-md)',
            padding: '32px 16px',
            textAlign: 'center',
            cursor: uploading ? 'not-allowed' : 'pointer',
            background: 'rgba(0,0,0,0.2)',
            transition: 'border-color 0.2s',
            marginBottom: '24px',
            opacity: uploading ? 0.6 : 1
          }}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleUpload} 
            style={{ display: 'none' }} 
            accept=".pdf,.doc,.docx,.txt"
          />
          <UploadCloud size={32} color={uploading ? 'var(--text-secondary)' : 'var(--accent-hover)'} style={{ marginBottom: '12px', margin: '0 auto' }} />
          <p style={{ fontSize: '14px', fontWeight: 500, margin: 0 }}>
            {uploading ? 'Analyzing Document...' : 'Upload Legal Text'}
          </p>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            PDF, DOCX, TXT up to 50MB
          </p>
        </motion.div>

        <AnimatePresence>
          {activeDocument && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              style={{
                background: 'rgba(139, 92, 246, 0.1)',
                border: '1px solid var(--accent-glow)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px'
              }}
            >
              <div style={{ background: 'var(--accent-base)', padding: '8px', borderRadius: '8px' }}>
                <FileText size={20} color="white" />
              </div>
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>Active Document</p>
                <p style={{ fontSize: '14px', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {activeDocument}
                </p>
              </div>
              <CheckCircle2 size={16} color="var(--success-base)" style={{ marginTop: '4px' }} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div style={{ padding: '24px', borderTop: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(0,0,0,0.3)', padding: '12px 16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', overflow: 'hidden' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--border-strong)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', fontWeight: 'bold' }}>
              {username.charAt(0).toUpperCase()}
            </div>
            <span style={{ fontSize: '14px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis' }}>{username}</span>
          </div>
          <motion.button 
            whileHover={{ scale: 1.1, color: 'var(--error-base)' }}
            whileTap={{ scale: 0.9 }}
            onClick={onLogout}
            style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px' }}
            title="Disconnect"
          >
            <LogOut size={18} />
          </motion.button>
        </div>
      </div>
    </motion.aside>
  )
}

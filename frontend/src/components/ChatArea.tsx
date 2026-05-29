import { useRef, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import TextareaAutosize from 'react-textarea-autosize'
import { Send, Sparkles, Plus, Download } from 'lucide-react'
// @ts-ignore
import html2pdf from 'html2pdf.js'
import MessageBubble from './MessageBubble'
import LoadingSkeleton from './LoadingSkeleton'
import { toast } from 'sonner'

interface Message {
  role: 'user' | 'ai'
  text: string
  timestamp: string
}

interface ChatAreaProps {
  token: string
  username: string
  activeDocument: string
  onDocumentChange: (docName: string) => void
}

const GATEWAY_BASE = import.meta.env.VITE_GATEWAY_BASE || 'http://localhost:3000'

export default function ChatArea({ token, username, activeDocument, onDocumentChange }: ChatAreaProps) {
  const [query, setQuery] = useState('')
  const [responses, setResponses] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [responses, loading])

  const getFormatTime = () => {
    return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: 'numeric', hour12: true }).format(new Date())
  }

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

  const submitQuery = async () => {
    if (!query.trim() || loading) return
    if (!activeDocument) {
      toast.error('Please upload a document to the Knowledge Base first.')
      return
    }

    const time = getFormatTime()
    setResponses(prev => [...prev, { role: 'user', text: query.trim(), timestamp: time }])
    const currentQuery = query.trim()
    setQuery('')
    setLoading(true)

    try {
      const res = await fetch(`${GATEWAY_BASE}/query`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: new URLSearchParams({ query: currentQuery, userid: username })
      })

      const data = await res.json()
      const replyTime = getFormatTime()
      
      if (res.ok) {
        setResponses(prev => [...prev, { role: 'ai', text: data.response || 'No response from AI.', timestamp: replyTime }])
      } else {
        toast.error(data.error || 'Failed to get response')
        setResponses(prev => [...prev, { role: 'ai', text: `Error: ${data.error || 'Failed to get response'}`, timestamp: replyTime }])
      }
    } catch (err) {
      toast.error('Could not connect to the Backend API.')
      setResponses(prev => [...prev, { role: 'ai', text: 'Error: Could not connect to the Backend API.', timestamp: getFormatTime() }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submitQuery()
    }
  }

  const exportChatToPDF = () => {
    const element = document.getElementById('chat-export-content')
    if (!element) return

    const toastId = toast.loading('Generating PDF...')

    const opt = {
      margin:       10,
      filename:     `LegalAI_Chat_${new Date().getTime()}.pdf`,
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#050505' },
      jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    }

    html2pdf().set(opt).from(element).save().then(() => {
      toast.success('Chat exported to PDF successfully!', { id: toastId })
    }).catch(() => {
      toast.error('Failed to export PDF', { id: toastId })
    })
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
      
      {/* Messages Area */}
      <div id="chat-export-content" style={{ flex: 1, overflowY: 'auto', padding: '40px 0', scrollBehavior: 'smooth' }}>
        {responses.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{ 
              height: '100%', display: 'flex', flexDirection: 'column', 
              alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)'
            }}
          >
            <Sparkles size={48} color="var(--accent-base)" style={{ marginBottom: '24px', opacity: 0.8 }} />
            <h1 style={{ fontSize: '28px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
              How can I assist you today?
            </h1>
            <p style={{ maxWidth: '400px', textAlign: 'center', lineHeight: 1.6 }}>
              Upload a legal document to the Knowledge Base, then ask me questions about its provisions, clauses, or obligations.
            </p>
          </motion.div>
        ) : (
          <div style={{ maxWidth: '1000px', margin: '0 auto', width: '100%', position: 'relative' }}>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={exportChatToPDF}
              title="Export Chat to PDF"
              style={{
                position: 'absolute',
                top: '-20px',
                right: '24px',
                background: 'var(--bg-surface)',
                backdropFilter: 'var(--glass-blur)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                width: '36px', height: '36px',
                borderRadius: '8px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', zIndex: 10,
                boxShadow: 'var(--glass-shadow)',
                transition: 'color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
            >
              <Download size={16} />
            </motion.button>
            
            <AnimatePresence initial={false}>
              {responses.map((r, i) => (
                <MessageBubble key={i} role={r.role} text={r.text} timestamp={r.timestamp} />
              ))}
              {loading && <LoadingSkeleton key="loading" />}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div style={{ 
        padding: '24px', 
        background: 'linear-gradient(to top, var(--bg-base) 60%, transparent)',
        display: 'flex', justifyContent: 'center'
      }}>
        <div style={{ 
          width: '100%', maxWidth: '800px', position: 'relative',
          background: 'var(--bg-surface)', backdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--glass-shadow)',
          display: 'flex', alignItems: 'flex-end', padding: '8px',
          transition: 'all 0.3s ease'
        }}
        className="chat-input-wrapper"
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleUpload} 
            style={{ display: 'none' }} 
            accept=".pdf,.doc,.docx,.txt"
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => !uploading && fileInputRef.current?.click()}
            disabled={uploading}
            title="Upload Document"
            style={{
              width: '40px', height: '40px', borderRadius: '12px', flexShrink: 0,
              background: 'transparent',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)', cursor: uploading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '4px', transition: 'all 0.2s ease',
              opacity: uploading ? 0.5 : 1
            }}
          >
            <Plus size={20} />
          </motion.button>
          
          <TextareaAutosize
            minRows={1}
            maxRows={6}
            placeholder="Query your legal documents..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            style={{
              flex: 1, background: 'transparent', border: 'none', color: 'var(--text-primary)',
              padding: '12px 16px', fontSize: '15px', resize: 'none', outline: 'none',
              fontFamily: 'var(--font-sans)', lineHeight: 1.5
            }}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={submitQuery}
            disabled={loading || !query.trim()}
            style={{
              width: '40px', height: '40px', borderRadius: '12px', flexShrink: 0,
              background: query.trim() ? 'linear-gradient(135deg, var(--accent-base), var(--accent-hover))' : 'var(--bg-surface-hover)',
              color: query.trim() ? 'white' : 'var(--text-secondary)',
              border: 'none', cursor: query.trim() ? 'pointer' : 'not-allowed',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '4px', transition: 'all 0.2s ease',
              boxShadow: query.trim() ? '0 4px 12px var(--accent-glow)' : 'none'
            }}
          >
            <Send size={18} style={{ marginLeft: '2px' }} />
          </motion.button>
        </div>
      </div>
    </div>
  )
}

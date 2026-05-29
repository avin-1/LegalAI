import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, X, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { toast } from 'sonner'

interface TextSelectionTooltipProps {
  token: string
}

const GATEWAY_BASE = import.meta.env.VITE_GATEWAY_BASE || 'http://localhost:3000'

export default function TextSelectionTooltip({ token }: TextSelectionTooltipProps) {
  const [selectedText, setSelectedText] = useState('')
  const [btnPos, setBtnPos] = useState({ top: 0, left: 0 })
  const [isTooltipVisible, setIsTooltipVisible] = useState(false)

  const [explanation, setExplanation] = useState('')
  const [isExplaining, setIsExplaining] = useState(false)
  const [showModal, setShowModal] = useState(false)

  const modalRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleMouseUp = (e: MouseEvent) => {
      if (showModal) return
      // Don't trigger on modal clicks
      if (modalRef.current?.contains(e.target as Node)) return

      setTimeout(() => {
        const selection = window.getSelection()
        if (selection && selection.toString().trim().length > 5) {
          const text = selection.toString().trim()
          const range = selection.getRangeAt(0)
          const rect = range.getBoundingClientRect()
          setSelectedText(text)
          setBtnPos({
            top: rect.top - 44,
            left: rect.left + rect.width / 2
          })
          setIsTooltipVisible(true)
        } else {
          setIsTooltipVisible(false)
        }
      }, 10)
    }

    const handleMouseDown = (e: MouseEvent) => {
      if (modalRef.current?.contains(e.target as Node)) return
      if (showModal) {
        setShowModal(false)
        setExplanation('')
        window.getSelection()?.removeAllRanges()
      }
    }

    document.addEventListener('mouseup', handleMouseUp)
    document.addEventListener('mousedown', handleMouseDown)
    return () => {
      document.removeEventListener('mouseup', handleMouseUp)
      document.removeEventListener('mousedown', handleMouseDown)
    }
  }, [showModal])

  const handleExplainClick = async (e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    setIsTooltipVisible(false)
    setShowModal(true)
    setIsExplaining(true)
    setExplanation('')

    try {
      const res = await fetch(`${GATEWAY_BASE}/explain`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({ text: selectedText })
      })
      const data = await res.json()
      if (res.ok) {
        setExplanation(data.response || 'No explanation generated.')
      } else {
        setExplanation(`Error: ${data.error || 'Failed to explain text'}`)
        toast.error('Explanation failed')
      }
    } catch {
      setExplanation('Error: Could not connect to the Backend API.')
      toast.error('Network Error')
    } finally {
      setIsExplaining(false)
    }
  }

  const closeModal = () => {
    setShowModal(false)
    setExplanation('')
    window.getSelection()?.removeAllRanges()
  }

  return createPortal(
    <>
      {/* Floating Explain Button */}
      <AnimatePresence>
        {isTooltipVisible && !showModal && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            style={{
              position: 'fixed',
              top: btnPos.top,
              left: btnPos.left,
              transform: 'translateX(-50%)',
              zIndex: 99999,
              pointerEvents: 'auto'
            }}
          >
            <button
              onMouseDown={e => e.preventDefault()}
              onClick={handleExplainClick}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                background: 'rgba(20,20,20,0.95)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255,255,255,0.15)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                color: '#fff',
                padding: '8px 14px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontFamily: 'Outfit, sans-serif',
                fontSize: '13px',
                fontWeight: 600,
                transition: 'all 0.2s ease',
                whiteSpace: 'nowrap'
              }}
            >
              <Sparkles size={14} color="#a78bfa" />
              ✨ Explain
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Full-Screen Modal — rendered via portal at body level */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.65)',
              backdropFilter: 'blur(6px)',
              zIndex: 99999,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '24px'
            }}
          >
            <motion.div
              ref={modalRef}
              initial={{ opacity: 0, y: 24, scale: 0.94 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.96 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              style={{
                width: '100%',
                maxWidth: '620px',
                background: 'rgba(18, 18, 22, 0.97)',
                backdropFilter: 'blur(40px)',
                border: '1px solid rgba(167,139,250,0.25)',
                borderRadius: '18px',
                boxShadow: '0 30px 90px rgba(0,0,0,0.7), 0 0 0 1px rgba(167,139,250,0.1)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                maxHeight: '80vh'
              }}
            >
              {/* Header */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '16px 24px',
                borderBottom: '1px solid rgba(255,255,255,0.07)',
                background: 'rgba(0,0,0,0.25)',
                flexShrink: 0
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Sparkles size={18} color="#a78bfa" />
                  <span style={{ fontSize: '15px', fontWeight: 700, color: '#fff', fontFamily: 'Outfit, sans-serif' }}>
                    AI Explanation
                  </span>
                  <span style={{
                    fontSize: '11px', fontWeight: 500,
                    background: 'rgba(167,139,250,0.15)',
                    color: '#a78bfa',
                    border: '1px solid rgba(167,139,250,0.3)',
                    borderRadius: '4px', padding: '2px 8px'
                  }}>
                    Simplified for everyone
                  </span>
                </div>
                <button
                  onClick={closeModal}
                  style={{
                    background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                    color: 'rgba(255,255,255,0.6)', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    width: '30px', height: '30px', borderRadius: '8px',
                    transition: 'all 0.2s'
                  }}
                >
                  <X size={16} />
                </button>
              </div>

              {/* Selected text snippet */}
              <div style={{
                margin: '16px 24px 0',
                padding: '12px 14px',
                background: 'rgba(255,255,255,0.04)',
                borderLeft: '3px solid #a78bfa',
                borderRadius: '4px',
                fontSize: '13px',
                color: 'rgba(255,255,255,0.5)',
                fontStyle: 'italic',
                lineHeight: 1.6,
                maxHeight: '80px',
                overflowY: 'auto',
                flexShrink: 0
              }}>
                "{selectedText.length > 200 ? selectedText.slice(0, 200) + '…' : selectedText}"
              </div>

              {/* Body */}
              <div style={{ padding: '20px 24px 24px', overflowY: 'auto', flex: 1 }}>
                {isExplaining ? (
                  <div style={{
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center',
                    gap: '16px', minHeight: '160px'
                  }}>
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                    >
                      <Loader2 size={32} color="#a78bfa" />
                    </motion.div>
                    <span style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)', fontFamily: 'Outfit, sans-serif' }}>
                      Breaking down legal language...
                    </span>
                  </div>
                ) : (
                  <div style={{
                    fontSize: '15px', lineHeight: 1.8,
                    color: 'rgba(255,255,255,0.88)',
                    fontFamily: 'Outfit, sans-serif'
                  }}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        table: ({ children }) => (
                          <div style={{ overflowX: 'auto', marginTop: '12px', marginBottom: '12px' }}>
                            <table style={{
                              width: '100%', borderCollapse: 'collapse',
                              fontSize: '13px', lineHeight: 1.5
                            }}>{children}</table>
                          </div>
                        ),
                        th: ({ children }) => (
                          <th style={{
                            padding: '8px 12px', textAlign: 'left',
                            background: 'rgba(167,139,250,0.15)',
                            borderBottom: '1px solid rgba(167,139,250,0.3)',
                            color: '#a78bfa', fontWeight: 600, whiteSpace: 'nowrap'
                          }}>{children}</th>
                        ),
                        td: ({ children }) => (
                          <td style={{
                            padding: '8px 12px',
                            borderBottom: '1px solid rgba(255,255,255,0.06)',
                            color: 'rgba(255,255,255,0.8)'
                          }}>{children}</td>
                        ),
                        tr: ({ children }) => (
                          <tr style={{ transition: 'background 0.15s' }}>{children}</tr>
                        ),
                        strong: ({ children }) => (
                          <strong style={{ color: '#fff', fontWeight: 700 }}>{children}</strong>
                        ),
                        p: ({ children }) => (
                          <p style={{ marginBottom: '10px', marginTop: 0 }}>{children}</p>
                        ),
                        li: ({ children }) => (
                          <li style={{ marginBottom: '6px' }}>{children}</li>
                        ),
                        ul: ({ children }) => (
                          <ul style={{ paddingLeft: '20px', marginBottom: '10px' }}>{children}</ul>
                        ),
                        ol: ({ children }) => (
                          <ol style={{ paddingLeft: '20px', marginBottom: '10px' }}>{children}</ol>
                        ),
                        h1: ({ children }) => (
                          <h1 style={{ fontSize: '18px', fontWeight: 700, color: '#fff', marginBottom: '8px', marginTop: '16px' }}>{children}</h1>
                        ),
                        h2: ({ children }) => (
                          <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#e5e5ff', marginBottom: '6px', marginTop: '14px' }}>{children}</h2>
                        ),
                        h3: ({ children }) => (
                          <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#c4b5fd', marginBottom: '4px', marginTop: '12px' }}>{children}</h3>
                        ),
                      }}
                    >
                      {explanation}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>,
    document.body
  )
}

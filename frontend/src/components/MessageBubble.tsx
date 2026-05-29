import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { motion } from 'framer-motion'
import { Bot, User } from 'lucide-react'

interface MessageProps {
  role: 'user' | 'ai'
  text: string
  timestamp: string
}

export default function MessageBubble({ role, text, timestamp }: MessageProps) {
  const isAI = role === 'ai'

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      style={{
        width: '100%',
        display: 'flex',
        justifyContent: isAI ? 'flex-start' : 'flex-end',
        padding: '0 24px',
        marginBottom: '24px'
      }}
    >
      <div style={{
        display: 'flex',
        gap: '16px',
        maxWidth: '85%',
        flexDirection: isAI ? 'row' : 'row-reverse'
      }}>
        {/* Avatar */}
        <div style={{
          width: '36px', height: '36px', flexShrink: 0,
          borderRadius: '12px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: isAI ? 'linear-gradient(135deg, var(--accent-base), var(--accent-hover))' : 'var(--bg-surface-hover)',
          boxShadow: isAI ? '0 4px 12px var(--accent-glow)' : 'none',
          border: isAI ? 'none' : '1px solid var(--border-subtle)'
        }}>
          {isAI ? <Bot size={20} color="white" /> : <User size={20} color="var(--text-primary)" />}
        </div>

        {/* Message Content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: isAI ? 'flex-start' : 'flex-end' }}>
          <div style={{
            background: isAI ? 'rgba(30, 30, 30, 0.4)' : 'var(--accent-base)',
            backdropFilter: isAI ? 'var(--glass-blur)' : 'none',
            border: isAI ? '1px solid var(--border-subtle)' : 'none',
            color: 'var(--text-primary)',
            padding: '16px 20px',
            borderRadius: isAI ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
            boxShadow: isAI ? 'var(--glass-shadow)' : '0 4px 15px var(--accent-glow)',
            fontSize: '15px',
            lineHeight: 1.6
          }}>
            {isAI ? (
              <ReactMarkdown
                className="markdown-body"
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || '')
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus as any}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ borderRadius: '8px', margin: '16px 0' }}
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    )
                  }
                }}
              >
                {text}
              </ReactMarkdown>
            ) : (
              <div style={{ whiteSpace: 'pre-wrap' }}>{text}</div>
            )}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', padding: '0 4px' }}>
            {timestamp}
          </span>
        </div>
      </div>
    </motion.div>
  )
}

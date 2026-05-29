import { motion } from 'framer-motion'
import { Bot } from 'lucide-react'

export default function LoadingSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      style={{
        width: '100%',
        display: 'flex',
        justifyContent: 'flex-start',
        padding: '0 24px',
        marginBottom: '24px'
      }}
    >
      <div style={{ display: 'flex', gap: '16px', maxWidth: '85%' }}>
        <div style={{
          width: '36px', height: '36px', flexShrink: 0,
          borderRadius: '12px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'linear-gradient(135deg, var(--accent-base), var(--accent-hover))',
          boxShadow: '0 4px 12px var(--accent-glow)'
        }}>
          <Bot size={20} color="white" />
        </div>

        <div style={{
          background: 'rgba(30, 30, 30, 0.4)',
          backdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-subtle)',
          padding: '16px 20px',
          borderRadius: '4px 16px 16px 16px',
          boxShadow: 'var(--glass-shadow)',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          height: '56px'
        }}>
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              animate={{ 
                scale: [1, 1.5, 1],
                opacity: [0.3, 1, 0.3]
              }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                ease: 'easeInOut',
                delay: i * 0.2
              }}
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'var(--accent-hover)'
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  )
}

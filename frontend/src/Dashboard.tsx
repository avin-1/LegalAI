import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import TextSelectionTooltip from './components/TextSelectionTooltip'

interface DashboardProps {
  token: string
  username: string
  onLogout: () => void
}

const GATEWAY_BASE = import.meta.env.VITE_GATEWAY_BASE || 'http://localhost:3000'

export default function Dashboard({ token, username, onLogout }: DashboardProps) {
  const [activeDocument, setActiveDocument] = useState<string>('')

  useEffect(() => {
    const fetchActiveDoc = async () => {
      try {
        const res = await fetch(`${GATEWAY_BASE}/upload?userid=${username}`, {
          method: 'GET',
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
          const data = await res.json()
          if (data.filename) {
            setActiveDocument(data.filename)
          }
        }
      } catch (err) {
        console.error("Failed to fetch active document", err)
      }
    }
    fetchActiveDoc()
  }, [token, username])

  return (
    <motion.div 
      className="dashboard-layout"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Sidebar 
        username={username} 
        token={token} 
        onLogout={onLogout} 
        activeDocument={activeDocument} 
        onDocumentChange={setActiveDocument} 
      />
      <ChatArea 
        token={token} 
        username={username} 
        activeDocument={activeDocument} 
        onDocumentChange={setActiveDocument}
      />
      <TextSelectionTooltip token={token} />
    </motion.div>
  )
}

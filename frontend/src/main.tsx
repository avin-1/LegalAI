import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ErrorBoundary } from 'react-error-boundary'
import './index.css'
import App from './App.tsx'

function Fallback({ error }: { error: Error }) {
  return (
    <div style={{ padding: '40px', color: 'red', background: '#fff', height: '100vh', width: '100vw' }}>
      <h1>Something went wrong:</h1>
      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{error.message}</pre>
      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '12px', marginTop: '20px' }}>{error.stack}</pre>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary FallbackComponent={Fallback}>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)

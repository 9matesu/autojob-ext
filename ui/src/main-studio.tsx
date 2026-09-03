import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import StudioApp from './StudioApp'
import { ErrorBoundary } from './ErrorBoundary'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <StudioApp />
    </ErrorBoundary>
  </StrictMode>,
)

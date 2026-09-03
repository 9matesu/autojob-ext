import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import SidePanelApp from './SidePanelApp'
import { ErrorBoundary } from './ErrorBoundary'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <SidePanelApp />
    </ErrorBoundary>
  </StrictMode>,
)

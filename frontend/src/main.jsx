import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './lib/AuthProvider.jsx'
import { Sentry, initAnalytics } from './lib/analytics'

initAnalytics()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Sentry.ErrorBoundary
        fallback={<p style={{ padding: '3rem 1.5rem' }}>Something went wrong. Please refresh the page.</p>}
      >
        <AuthProvider>
          <App />
        </AuthProvider>
      </Sentry.ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
)

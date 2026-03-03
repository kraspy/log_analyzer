/**
 * Application entry point — mounts the React root into the DOM.
 *
 * Wraps {@link App} in `StrictMode` for development warnings.
 * @module main
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

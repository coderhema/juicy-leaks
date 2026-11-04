import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@astryxdesign/core/reset.css'
import '@astryxdesign/core/astryx.css'
import { Theme } from '@astryxdesign/core/theme'
import { defineTheme } from '@astryxdesign/core/theme'
import { themes, defaultThemeSlug } from './astryx-themes'
import App from './App'

// Neutral Astryx theme, with the GuardRail Lens navy + cyan brand on top.
const guardrail = defineTheme({
  name: 'guardrail',
  extends: themes[defaultThemeSlug],
  tokens: {
    '--color-accent': ['#0e7490', '#22c3ee'],
    '--color-text-primary': ['#0b1f3a', '#ffffff'],
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Theme theme={guardrail} mode="light">
      <App />
    </Theme>
  </StrictMode>,
)

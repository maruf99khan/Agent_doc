import { useState, useEffect } from 'react'

const PALETTES = [
  ['#0a0a2e', '#1a0a3e', '#0a2a3e', '#2a1a0e'],
  ['#0a0a2e', '#2a0a2e', '#0a2a2e', '#1a2a0e'],
  ['#0a0a2e', '#0a1a3e', '#1a0a3e', '#0a2a1e'],
  ['#0a0a2e', '#1a0a3e', '#0a2a2e', '#2a0a1e'],
]

export function useGradient() {
  const [palette, setPalette] = useState(PALETTES[0])

  useEffect(() => {
    const interval = setInterval(() => {
      setPalette(PALETTES[Math.floor(Math.random() * PALETTES.length)])
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  return palette
}

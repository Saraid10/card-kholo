// Plays backend audio (base64 WAV from Bulbul). When there is none (mocks, or TTS failed),
// falls back to the browser's speech synthesis so the screen still talks.
import { useCallback, useEffect, useRef, useState } from 'react'
import type { Lang } from '../api/types'
import { speechLang } from './format'

export type VoiceState = 'idle' | 'playing' | 'done'

// Only one player sounds at a time across the app.
let stopActive: (() => void) | null = null

interface Opts {
  onStart?: () => void
  onComplete?: () => void
}

export function useVoice(audioB64: string | null | undefined, text: string, lang: Lang, opts: Opts = {}) {
  const [state, setState] = useState<VoiceState>('idle')
  const [progress, setProgress] = useState(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const timer = useRef<number | null>(null)
  const optsRef = useRef(opts)
  optsRef.current = opts

  const stop = useCallback(() => {
    audioRef.current?.pause()
    audioRef.current = null
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel()
    if (timer.current) window.clearInterval(timer.current)
    timer.current = null
    setState((s) => (s === 'playing' ? 'idle' : s))
  }, [])

  useEffect(() => stop, [stop])

  const finish = useCallback(() => {
    if (timer.current) window.clearInterval(timer.current)
    timer.current = null
    setProgress(1)
    setState('done')
    optsRef.current.onComplete?.()
  }, [])

  const play = useCallback(() => {
    stopActive?.()
    stop()
    stopActive = stop
    setProgress(0)
    setState('playing')

    if (audioB64) {
      const a = new Audio(`data:audio/wav;base64,${audioB64}`)
      audioRef.current = a
      a.ontimeupdate = () => a.duration && setProgress(a.currentTime / a.duration)
      a.onended = finish
      a.onerror = () => setState('idle')
      a.play().then(() => optsRef.current.onStart?.()).catch(() => setState('idle'))
      return
    }

    if (!('speechSynthesis' in window)) {
      setState('idle')
      return
    }
    const u = new SpeechSynthesisUtterance(text)
    u.lang = speechLang[lang]
    u.rate = 0.92
    const voice = window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith(speechLang[lang].slice(0, 2)))
    if (voice) u.voice = voice
    // Speech synthesis has no progress events everywhere, so estimate from length.
    const est = Math.max(2500, text.length * 75)
    const t0 = Date.now()
    timer.current = window.setInterval(() => setProgress(Math.min(0.97, (Date.now() - t0) / est)), 120)
    u.onstart = () => optsRef.current.onStart?.()
    u.onend = finish
    u.onerror = () => {
      if (timer.current) window.clearInterval(timer.current)
      setState('idle')
    }
    window.speechSynthesis.speak(u)
  }, [audioB64, text, lang, stop, finish])

  return { state, progress, play, stop }
}

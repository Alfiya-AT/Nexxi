// src/hooks/useVoiceInput.ts
import { useState, useRef, useCallback, useEffect } from 'react'
import toast from 'react-hot-toast'
import { isSpeechRecognitionSupported } from '@/utils/validators'
import type { VoiceState } from '@/types/chat.types'

interface UseVoiceInputOptions {
    onTranscript?: (text: string) => void  // Called with final transcript
    autoStopMs?: number                  // Max recording duration (default 10s)
    language?: string                  // BCP-47 language tag (default 'en-US')
}

interface UseVoiceInputReturn {
    voiceState: VoiceState
    transcript: string               // Live partial transcript
    isSupported: boolean
    startRecording: () => void
    stopRecording: () => void
    resetTranscript: () => void
}

export function useVoiceInput({
    onTranscript,
    autoStopMs = 10_000,
    language = 'en-US',
}: UseVoiceInputOptions = {}): UseVoiceInputReturn {

    const [voiceState, setVoiceState] = useState<VoiceState>('idle')
    const [transcript, setTranscript] = useState('')
    const recognitionRef = useRef<SpeechRecognition | null>(null)
    const autoStopRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const isSupported = isSpeechRecognitionSupported()

    // ── Cleanup on unmount ────────────────────────────────────────
    useEffect(() => {
        return () => {
            recognitionRef.current?.abort()
            if (autoStopRef.current) clearTimeout(autoStopRef.current)
        }
    }, [])

    const startRecording = useCallback(() => {
        if (!isSupported) {
            toast.error('Voice input is not supported in your browser.')
            return
        }
        if (voiceState === 'listening') return

        // Request mic permission implicitly through SpeechRecognition
        const SpeechRecognition =
            window.SpeechRecognition ?? (window as Window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition
        if (!SpeechRecognition) return

        const recognition = new SpeechRecognition()
        recognition.continuous = true
        recognition.interimResults = true
        recognition.lang = language
        recognition.maxAlternatives = 1

        recognition.onstart = () => {
            setVoiceState('listening')
            setTranscript('')
            toast.success('Listening…', { icon: '🎙', id: 'voice-listening' })
        }

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            let interim = ''
            let finalText = ''
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i]
                if (result.isFinal) {
                    finalText += result[0].transcript
                } else {
                    interim += result[0].transcript
                }
            }
            setTranscript(finalText || interim)
        }

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            toast.dismiss('voice-listening')
            if (event.error === 'not-allowed') {
                toast.error('Microphone permission denied.')
                setVoiceState('error')
            } else if (event.error === 'network') {
                toast.error('Network error with voice recognition.')
                setVoiceState('error')
            } else {
                setVoiceState('idle')
            }
            recognitionRef.current = null
        }

        recognition.onend = () => {
            toast.dismiss('voice-listening')
            setVoiceState('processing')

            // Grab final transcript and pass to callback
            setTimeout(() => {
                setVoiceState('idle')
                const finalTranscript = transcript || ''
                if (finalTranscript.trim() && onTranscript) {
                    onTranscript(finalTranscript.trim())
                }
            }, 300)

            if (autoStopRef.current) clearTimeout(autoStopRef.current)
            recognitionRef.current = null
        }

        recognitionRef.current = recognition
        recognition.start()

        // Auto-stop after `autoStopMs`
        autoStopRef.current = setTimeout(() => {
            recognition.stop()
        }, autoStopMs)

    }, [isSupported, voiceState, language, autoStopMs, onTranscript, transcript])

    const stopRecording = useCallback(() => {
        if (autoStopRef.current) clearTimeout(autoStopRef.current)
        recognitionRef.current?.stop()
    }, [])

    const resetTranscript = useCallback(() => {
        setTranscript('')
    }, [])

    return {
        voiceState,
        transcript,
        isSupported,
        startRecording,
        stopRecording,
        resetTranscript,
    }
}

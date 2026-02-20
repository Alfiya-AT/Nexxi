// src/components/chat/VoiceInput.tsx
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { Tooltip } from '@/components/ui/Tooltip'
import { useVoiceInput } from '@/hooks/useVoiceInput'

interface VoiceInputProps {
    onTranscript: (text: string) => void
    disabled?: boolean
}

export function VoiceInput({ onTranscript, disabled }: VoiceInputProps) {
    const { voiceState, transcript, isSupported, startRecording, stopRecording } = useVoiceInput({
        onTranscript,
        autoStopMs: 10_000,
    })

    if (!isSupported) {
        return (
            <Tooltip content="Voice not supported in this browser">
                <button
                    disabled
                    className="p-2 rounded-xl text-nexxi-text-muted opacity-30 cursor-not-allowed"
                >
                    <MicOff className="w-5 h-5" />
                </button>
            </Tooltip>
        )
    }

    const isListening = voiceState === 'listening'
    const isProcessing = voiceState === 'processing'

    const handleClick = () => {
        if (isListening) {
            stopRecording()
        } else {
            startRecording()
        }
    }

    return (
        <div className="relative">
            <Tooltip content={isListening ? 'Stop recording' : 'Voice input'}>
                <motion.button
                    type="button"
                    onClick={handleClick}
                    disabled={disabled || isProcessing}
                    whileTap={{ scale: 0.9 }}
                    className={clsx(
                        'relative p-2 rounded-xl transition-all duration-200',
                        isListening
                            ? 'text-nexxi-error bg-nexxi-error/10'
                            : 'text-nexxi-text-muted hover:text-nexxi-text-primary hover:bg-nexxi-bg-tertiary',
                        (disabled || isProcessing) && 'opacity-40 cursor-not-allowed'
                    )}
                    aria-label={isListening ? 'Stop recording' : 'Start voice input'}
                >
                    {/* Pulsing ring when listening */}
                    {isListening && (
                        <motion.span
                            className="absolute inset-0 rounded-xl border-2 border-nexxi-error"
                            animate={{ scale: [1, 1.3, 1], opacity: [1, 0, 1] }}
                            transition={{ duration: 1.2, repeat: Infinity }}
                        />
                    )}

                    {isProcessing
                        ? <Loader2 className="w-5 h-5 animate-spin" />
                        : isListening
                            ? <Mic className="w-5 h-5 animate-recording-ring" />
                            : <Mic className="w-5 h-5" />
                    }
                </motion.button>
            </Tooltip>

            {/* Live transcript preview */}
            <AnimatePresence>
                {isListening && transcript && (
                    <motion.div
                        initial={{ opacity: 0, y: 8, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 8 }}
                        className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-64 p-3 rounded-xl glass text-xs text-nexxi-text-secondary border-nexxi-accent/30"
                        style={{ border: '1px solid rgba(124,58,237,0.3)' }}
                    >
                        <p className="font-medium text-nexxi-text-muted mb-1 text-[10px] uppercase tracking-wider">
                            Live transcript
                        </p>
                        <p className="text-nexxi-text-primary">{transcript}</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

// src/components/chat/ChatInput.tsx
import { useState, useRef, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Send, Square } from 'lucide-react'
import { clsx } from 'clsx'
import { VoiceInput } from './VoiceInput'
import { FileUpload } from './FileUpload'
import { useFileUpload } from '@/hooks/useFileUpload'
import { validateMessage } from '@/utils/validators'

const MAX_CHARS = 1000

interface ChatInputProps {
    onSend: (text: string, files?: ReturnType<typeof useFileUpload>['uploadedFiles']) => void
    onCancel?: () => void
    isLoading: boolean
    isStreaming: boolean
    disabled?: boolean
}

export function ChatInput({ onSend, onCancel, isLoading, isStreaming, disabled }: ChatInputProps) {
    const [text, setText] = useState('')
    const [error, setError] = useState<string | null>(null)
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const { uploadedFiles, handleFiles, removeFile, clearFiles } = useFileUpload()

    const isBusy = isLoading || isStreaming
    const canSend = text.trim().length > 0 && !isBusy && !disabled
    const charCount = text.length
    const isNearLimit = charCount > MAX_CHARS * 0.85

    // Auto-resize textarea
    useEffect(() => {
        const ta = textareaRef.current
        if (!ta) return
        ta.style.height = 'auto'
        ta.style.height = Math.min(ta.scrollHeight, 140) + 'px'
    }, [text])

    const handleSend = useCallback(() => {
        const validation = validateMessage(text)
        if (!validation.valid) {
            setError(validation.error ?? 'Invalid message')
            return
        }
        setError(null)
        onSend(text.trim(), uploadedFiles.length > 0 ? uploadedFiles : undefined)
        setText('')
        clearFiles()
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.focus()
        }
    }, [text, uploadedFiles, onSend, clearFiles])

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            if (canSend) handleSend()
        }
    }

    const handleVoiceTranscript = useCallback((transcript: string) => {
        setText(prev => prev ? `${prev} ${transcript}` : transcript)
        textareaRef.current?.focus()
    }, [])

    return (
        <div className="relative flex-shrink-0">
            {/* File preview rack — rendered above input bar */}
            <div className="relative">
                <FileUpload
                    uploadedFiles={uploadedFiles}
                    onFiles={handleFiles}
                    onRemove={removeFile}
                    disabled={disabled || isBusy}
                />
            </div>

            {/* Input bar */}
            <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                className="mx-4 mb-4 rounded-2xl border transition-all duration-200"
                style={{
                    background: 'rgba(26,26,40,0.85)',
                    backdropFilter: 'blur(16px)',
                    borderColor: text ? 'rgba(124,58,237,0.5)' : '#2D2D3D',
                    boxShadow: text ? '0 0 0 3px rgba(124,58,237,0.08)' : 'none',
                }}
            >
                {/* Textarea */}
                <textarea
                    ref={textareaRef}
                    id="chat-input"
                    value={text}
                    onChange={e => { setText(e.target.value); setError(null) }}
                    onKeyDown={handleKeyDown}
                    placeholder="Message Nexxi... (Enter to send, Shift+Enter for new line)"
                    disabled={disabled}
                    rows={1}
                    maxLength={MAX_CHARS}
                    className={clsx(
                        'w-full px-4 pt-3.5 pb-2 bg-transparent resize-none text-sm text-nexxi-text-primary',
                        'placeholder-nexxi-text-muted focus:outline-none leading-relaxed',
                        disabled && 'opacity-50 cursor-not-allowed'
                    )}
                    style={{ maxHeight: '140px' }}
                    aria-label="Chat message input"
                />

                {/* Bottom toolbar */}
                <div className="flex items-center justify-between px-3 pb-3 gap-2">
                    <div className="flex items-center gap-1">
                        {/* File attach */}
                        <div className="relative">
                            <FileUpload
                                uploadedFiles={[]}          // inner instance — just button
                                onFiles={handleFiles}
                                onRemove={removeFile}
                                disabled={disabled || isBusy}
                            />
                        </div>
                        {/* Voice */}
                        <VoiceInput onTranscript={handleVoiceTranscript} disabled={disabled || isBusy} />
                    </div>

                    <div className="flex items-center gap-2">
                        {/* Char counter */}
                        <span className={clsx(
                            'text-[10px] tabular-nums transition-colors',
                            isNearLimit ? 'text-nexxi-warning' : 'text-nexxi-text-muted',
                            charCount >= MAX_CHARS && 'text-nexxi-error'
                        )}>
                            {charCount}/{MAX_CHARS}
                        </span>

                        {/* Cancel / Send button */}
                        {isBusy ? (
                            <motion.button
                                whileTap={{ scale: 0.9 }}
                                onClick={onCancel}
                                className="flex items-center justify-center w-9 h-9 rounded-xl bg-nexxi-error/20 border border-nexxi-error/30 text-nexxi-error transition-all duration-200 hover:bg-nexxi-error/30"
                                aria-label="Stop generation"
                            >
                                <Square className="w-4 h-4 fill-current" />
                            </motion.button>
                        ) : (
                            <motion.button
                                whileTap={{ scale: 0.9 }}
                                onClick={handleSend}
                                disabled={!canSend}
                                className={clsx(
                                    'flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-200',
                                    canSend
                                        ? 'text-white'
                                        : 'bg-nexxi-bg-tertiary text-nexxi-text-muted cursor-not-allowed'
                                )}
                                style={canSend ? {
                                    background: 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)',
                                    boxShadow: '0 0 16px rgba(124,58,237,0.4)',
                                } : {}}
                                aria-label="Send message"
                            >
                                <Send className="w-4 h-4" />
                            </motion.button>
                        )}
                    </div>
                </div>

                {/* Error state */}
                {error && (
                    <p className="px-4 pb-2 text-xs text-nexxi-error">{error}</p>
                )}
            </motion.div>

            {/* Hint text */}
            <p className="text-center text-[10px] text-nexxi-text-muted pb-2">
                Nexxi may produce inaccurate information. Always verify important answers.
            </p>
        </div>
    )
}

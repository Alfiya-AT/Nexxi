// src/components/chat/ChatWindow.tsx
import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, MessageSquare } from 'lucide-react'
import { ChatBubble } from './ChatBubble'
import { TypingIndicator } from './TypingIndicator'
import { ChatInput } from './ChatInput'
import { useChat } from '@/hooks/useChat'
import { useChatStore } from '@/store/chatStore'

export function ChatWindow() {
    const { messages, isLoading, isStreaming, sendChat, cancelRequest } = useChat()
    const { error } = useChatStore()
    const bottomRef = useRef<HTMLDivElement>(null)
    const scrollRef = useRef<HTMLDivElement>(null)

    // Auto-scroll to bottom on new messages / streaming
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }, [messages, isStreaming])

    const isEmpty = messages.length === 0

    return (
        <div className="flex flex-col flex-1 min-h-0">

            {/* ── Message area ──────────────────────────────────────── */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto px-4 py-6 space-y-6"
                style={{ scrollBehavior: 'smooth' }}
            >
                {/* Empty state */}
                <AnimatePresence>
                    {isEmpty && (
                        <motion.div
                            initial={{ opacity: 0, y: 24 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -16 }}
                            transition={{ duration: 0.4 }}
                            className="flex flex-col items-center justify-center h-full min-h-[60vh] gap-6 text-center px-8"
                        >
                            {/* Animated logo */}
                            <motion.div
                                animate={{
                                    boxShadow: [
                                        '0 0 30px rgba(124,58,237,0.3)',
                                        '0 0 60px rgba(124,58,237,0.6)',
                                        '0 0 30px rgba(124,58,237,0.3)',
                                    ],
                                }}
                                transition={{ duration: 2.5, repeat: Infinity }}
                                className="w-20 h-20 rounded-2xl flex items-center justify-center text-3xl font-bold text-white"
                                style={{ background: 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)' }}
                            >
                                N
                            </motion.div>

                            <div className="space-y-2">
                                <h2 className="text-2xl font-bold gradient-text">
                                    Hey! I'm Nexxi ⚡
                                </h2>
                                <p className="text-nexxi-text-secondary text-base">
                                    What can I help you with today?
                                </p>
                            </div>

                            {/* Quick start suggestions */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg mt-2">
                                {SUGGESTIONS.map((s, i) => (
                                    <motion.button
                                        key={s.text}
                                        initial={{ opacity: 0, y: 12 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.15 + i * 0.08 }}
                                        onClick={() => sendChat(s.text)}
                                        className="flex items-start gap-3 p-4 rounded-xl border border-nexxi-border bg-nexxi-bg-secondary hover:border-nexxi-accent/50 hover:bg-nexxi-bg-tertiary transition-all duration-200 text-left group"
                                    >
                                        <span className="text-2xl leading-none">{s.icon}</span>
                                        <div>
                                            <p className="text-sm font-medium text-nexxi-text-primary group-hover:text-nexxi-accent transition-colors">
                                                {s.label}
                                            </p>
                                            <p className="text-xs text-nexxi-text-muted mt-0.5">{s.text}</p>
                                        </div>
                                    </motion.button>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Messages */}
                {messages.map((msg, idx) => (
                    <ChatBubble key={msg.id} message={msg} index={idx} />
                ))}

                {/* Typing indicator: show only when loading but last message not yet streaming */}
                <TypingIndicator visible={isLoading && !isStreaming} />

                {/* Error banner */}
                <AnimatePresence>
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="flex items-center gap-2 px-4 py-3 rounded-xl bg-nexxi-error/10 border border-nexxi-error/30 text-nexxi-error text-sm mx-4"
                        >
                            <Zap className="w-4 h-4 flex-shrink-0" />
                            {error}
                        </motion.div>
                    )}
                </AnimatePresence>

                <div ref={bottomRef} />
            </div>

            {/* ── Input bar (fixed at bottom) ────────────────────── */}
            <ChatInput
                onSend={(text, files) => sendChat(text, files)}
                onCancel={cancelRequest}
                isLoading={isLoading}
                isStreaming={isStreaming}
            />
        </div>
    )
}

// Quick-start suggestions for empty state
const SUGGESTIONS = [
    { icon: '💡', label: 'Explain a concept', text: 'Explain how neural networks work in simple terms' },
    { icon: '✍️', label: 'Help me write', text: 'Write a professional email to reschedule a meeting' },
    { icon: '🐛', label: 'Debug my code', text: 'Help me debug this Python code:' },
    { icon: '🌍', label: 'Translate text', text: 'Translate "Hello, how are you?" into French, Spanish, and Japanese' },
]

// src/store/chatStore.ts
import { create } from 'zustand'
import { persist, devtools } from 'zustand/middleware'
import { v4 as uuidv4 } from 'uuid'
import type { Message, Session } from '@/types/chat.types'
import { extractSessionTitle } from '@/utils/formatters'

interface ChatStore {
    // ── Message state ───────────────────────────────────────────
    messages: Message[]
    isLoading: boolean
    isStreaming: boolean
    error: string | null

    // ── Session state ───────────────────────────────────────────
    sessions: Session[]
    activeSessionId: string | null

    // ── Message actions ─────────────────────────────────────────
    addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => Message
    updateLastMessage: (token: string) => void       // append streaming token
    setLastMessageDone: (meta?: { tokensUsed?: number; responseTimeMs?: number }) => void
    setLastMessageError: () => void
    clearMessages: () => void

    // ── Loading/error ───────────────────────────────────────────
    setLoading: (loading: boolean) => void
    setStreaming: (streaming: boolean) => void
    setError: (error: string | null) => void

    // ── Session actions ──────────────────────────────────────────
    createNewSession: () => string
    setActiveSession: (sessionId: string) => void
    updateSessionMeta: (sessionId: string, data: Partial<Session>) => void
    deleteSession: (sessionId: string) => void
    getActiveSession: () => Session | undefined
}

export const useChatStore = create<ChatStore>()(
    devtools(
        persist(
            (set, get) => ({
                // ── Initial state ─────────────────────────────────────
                messages: [],
                isLoading: false,
                isStreaming: false,
                error: null,
                sessions: [],
                activeSessionId: null,

                // ── Message actions ───────────────────────────────────
                addMessage: (msg) => {
                    const message: Message = {
                        ...msg,
                        id: uuidv4(),
                        timestamp: new Date(),
                    }
                    set((state) => ({ messages: [...state.messages, message], error: null }))

                    // Update session metadata
                    const { activeSessionId, sessions } = get()
                    if (activeSessionId) {
                        const hasSession = sessions.some(s => s.id === activeSessionId)
                        if (!hasSession) {
                            // Auto-create session entry on first message
                            const title = msg.role === 'user'
                                ? extractSessionTitle(msg.content)
                                : 'New Chat'
                            set((state) => ({
                                sessions: [{
                                    id: activeSessionId,
                                    title,
                                    createdAt: new Date(),
                                    updatedAt: new Date(),
                                    messageCount: 1,
                                    preview: msg.content.slice(0, 60),
                                }, ...state.sessions],
                            }))
                        } else {
                            set((state) => ({
                                sessions: state.sessions.map(s =>
                                    s.id === activeSessionId
                                        ? { ...s, updatedAt: new Date(), messageCount: s.messageCount + 1, preview: msg.content.slice(0, 60) }
                                        : s
                                ),
                            }))
                        }
                    }
                    return message
                },

                updateLastMessage: (token) => {
                    set((state) => {
                        const messages = [...state.messages]
                        const last = messages[messages.length - 1]
                        if (last && last.role === 'assistant') {
                            messages[messages.length - 1] = {
                                ...last,
                                content: last.content + token,
                                isStreaming: true,
                            }
                        }
                        return { messages }
                    })
                },

                setLastMessageDone: (meta) => {
                    set((state) => {
                        const messages = [...state.messages]
                        const last = messages[messages.length - 1]
                        if (last && last.role === 'assistant') {
                            messages[messages.length - 1] = {
                                ...last,
                                isStreaming: false,
                                tokensUsed: meta?.tokensUsed,
                                responseTimeMs: meta?.responseTimeMs,
                            }
                        }
                        return { messages, isStreaming: false, isLoading: false }
                    })
                },

                setLastMessageError: () => {
                    set((state) => {
                        const messages = [...state.messages]
                        const last = messages[messages.length - 1]
                        if (last && last.role === 'assistant') {
                            messages[messages.length - 1] = { ...last, error: true, isStreaming: false }
                        }
                        return { messages, isStreaming: false, isLoading: false }
                    })
                },

                clearMessages: () => set({ messages: [], error: null }),

                // ── Loading/error ──────────────────────────────────────
                setLoading: (loading) => set({ isLoading: loading }),
                setStreaming: (streaming) => set({ isStreaming: streaming }),
                setError: (error) => set({ error }),

                // ── Session actions ────────────────────────────────────
                createNewSession: () => {
                    const id = uuidv4()
                    set({ activeSessionId: id, messages: [], error: null, isLoading: false, isStreaming: false })
                    return id
                },

                setActiveSession: (sessionId) => {
                    set({ activeSessionId: sessionId, messages: [], error: null })
                },

                updateSessionMeta: (sessionId, data) => {
                    set((state) => ({
                        sessions: state.sessions.map(s =>
                            s.id === sessionId ? { ...s, ...data } : s
                        ),
                    }))
                },

                deleteSession: (sessionId) => {
                    set((state) => {
                        const remaining = state.sessions.filter(s => s.id !== sessionId)
                        const isActive = state.activeSessionId === sessionId
                        return {
                            sessions: remaining,
                            activeSessionId: isActive ? (remaining[0]?.id ?? null) : state.activeSessionId,
                            messages: isActive ? [] : state.messages,
                        }
                    })
                },

                getActiveSession: () => {
                    const { sessions, activeSessionId } = get()
                    return sessions.find(s => s.id === activeSessionId)
                },
            }),
            {
                name: 'nexxi-chat-store',
                // Only persist sessions list (not message content for privacy)
                partialize: (state) => ({
                    sessions: state.sessions,
                    activeSessionId: state.activeSessionId,
                }),
            }
        ),
        { name: 'NexiiChatStore' }
    )
)

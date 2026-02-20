// src/hooks/useChat.ts
import { useRef, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import toast from 'react-hot-toast'
import { useChatStore } from '@/store/chatStore'
import { sendMessage, sendMessageStream } from '@/services/chatService'
import type { UploadedFile } from '@/types/chat.types'

export function useChat() {
    const {
        activeSessionId, createNewSession,
        addMessage, updateLastMessage, setLastMessageDone, setLastMessageError,
        setLoading, setStreaming, setError,
        messages, isLoading, isStreaming, error,
    } = useChatStore()

    // AbortController for cancelling in-flight requests
    const abortRef = useRef<AbortController | null>(null)

    const getOrCreateSession = useCallback((): string => {
        if (activeSessionId) return activeSessionId
        return createNewSession()
    }, [activeSessionId, createNewSession])

    /**
     * Send a message to Nexxi.
     * Automatically tries streaming first; falls back to standard if SSE fails.
     */
    const sendChat = useCallback(async (
        text: string,
        files?: UploadedFile[],
        stream = true
    ) => {
        if (isLoading || isStreaming) {
            // Cancel ongoing request first
            abortRef.current?.abort()
        }

        const sessionId = getOrCreateSession()
        const trimmed = text.trim()
        if (!trimmed) return

        // ── Optimistic: add user message immediately ──────────────
        addMessage({ role: 'user', content: trimmed, files })

        // ── Add empty assistant placeholder for streaming ─────────
        addMessage({ role: 'assistant', content: '', isStreaming: true })

        setLoading(true)
        setError(null)

        const controller = new AbortController()
        abortRef.current = controller

        const request = {
            session_id: sessionId,
            message: trimmed,
            stream,
            files: files?.map(f => f.url),
        }

        try {
            if (stream) {
                setStreaming(true)

                let streamed = false
                await sendMessageStream(
                    request,
                    // onToken
                    (token) => {
                        streamed = true
                        updateLastMessage(token)
                    },
                    // onDone
                    (meta) => {
                        setLastMessageDone({ tokensUsed: meta.tokensUsed, responseTimeMs: meta.responseTimeMs })
                    },
                    // onError — fall back to standard mode
                    async (_err) => {
                        // Streaming failed: try standard request
                        try {
                            const res = await sendMessage({ ...request, stream: false })
                            // Replace empty placeholder with actual content
                            setLastMessageDone({ tokensUsed: res.tokens_used, responseTimeMs: res.response_time_ms })
                            // Simulate word-by-word reveal for UX
                            await _revealText(res.message, updateLastMessage, setLastMessageDone, {
                                tokensUsed: res.tokens_used,
                                responseTimeMs: res.response_time_ms,
                            })
                        } catch (fallbackErr) {
                            setLastMessageError()
                            setError('Failed to get a response. Please try again.')
                            toast.error('Connection failed. Check if the backend is running.')
                        }
                    },
                    controller.signal,
                )

                // If streaming yielded nothing, try standard
                if (!streamed) {
                    const res = await sendMessage({ ...request, stream: false })
                    await _revealText(res.message, updateLastMessage, setLastMessageDone, {
                        tokensUsed: res.tokens_used,
                        responseTimeMs: res.response_time_ms,
                    })
                }

            } else {
                // Standard non-streaming call
                const res = await sendMessage(request)
                // Simulate word-by-word reveal for visual polish
                await _revealText(res.message, updateLastMessage, setLastMessageDone, {
                    tokensUsed: res.tokens_used,
                    responseTimeMs: res.response_time_ms,
                })
            }

        } catch (err) {
            if ((err as Error).name === 'AbortError') return
            setLastMessageError()
            const msg = (err as Error).message || 'An unexpected error occurred.'
            setError(msg)
            toast.error(msg)
        } finally {
            setLoading(false)
            setStreaming(false)
        }
    }, [
        isLoading, isStreaming, getOrCreateSession,
        addMessage, updateLastMessage, setLastMessageDone, setLastMessageError,
        setLoading, setStreaming, setError,
    ])

    /** Cancel the current in-flight request */
    const cancelRequest = useCallback(() => {
        abortRef.current?.abort()
        setLoading(false)
        setStreaming(false)
        setLastMessageError()
    }, [setLoading, setStreaming, setLastMessageError])

    return {
        messages,
        isLoading,
        isStreaming,
        error,
        sendChat,
        cancelRequest,
    }
}

// ── Helper: reveal text word-by-word (simulate streaming) ──────
async function _revealText(
    fullText: string,
    onToken: (t: string) => void,
    onDone: (meta: { tokensUsed?: number; responseTimeMs?: number }) => void,
    meta: { tokensUsed: number; responseTimeMs: number },
    delayMs = 18
) {
    const words = fullText.split(' ')
    for (let i = 0; i < words.length; i++) {
        const sep = i < words.length - 1 ? ' ' : ''
        onToken(words[i] + sep)
        await new Promise(r => setTimeout(r, delayMs))
    }
    onDone(meta)
}

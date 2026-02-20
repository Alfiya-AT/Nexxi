// src/services/chatService.ts
import api, { BASE_URL } from './api'
import type { ChatRequest, ChatResponse, StreamChunk } from '@/types/chat.types'

const API_KEY = import.meta.env.VITE_API_KEY || ''

// ── Standard (non-streaming) chat ─────────────────────────────
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const { data } = await api.post<ChatResponse>('/v1/chat', {
        ...request,
        stream: false,
    })
    return data
}

// ── Streaming chat via SSE using fetch ReadableStream ──────────
// (EventSource doesn't support POST, so we use fetch streaming)
export async function sendMessageStream(
    request: ChatRequest,
    onToken: (token: string) => void,
    onDone: (meta: { tokensUsed: number; responseTimeMs: number; sessionId: string }) => void,
    onError: (error: Error) => void,
    signal?: AbortSignal
): Promise<void> {
    const url = `${BASE_URL}/v1/chat/stream`

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_KEY,
                'Accept': 'text/event-stream',
            },
            body: JSON.stringify({ ...request, stream: true }),
            signal,
        })

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            throw new Error((errorData as { detail?: string }).detail ?? `HTTP ${response.status}`)
        }

        if (!response.body) {
            throw new Error('No response body received from streaming endpoint.')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() ?? ''

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue
                const raw = line.slice(6).trim()
                if (raw === '[DONE]') return

                try {
                    const chunk: StreamChunk = JSON.parse(raw)
                    if (chunk.finished) {
                        onDone({
                            tokensUsed: 0,
                            responseTimeMs: 0,
                            sessionId: chunk.session_id,
                        })
                        return
                    }
                    if (chunk.delta) {
                        onToken(chunk.delta)
                    }
                } catch {
                    // Ignore malformed chunks
                }
            }
        }
    } catch (err) {
        if ((err as Error).name === 'AbortError') return   // Cancelled — not an error
        onError(err instanceof Error ? err : new Error(String(err)))
    }
}

// ── Delete / clear session history ────────────────────────────
export async function clearSession(sessionId: string): Promise<void> {
    await api.delete('/v1/chat/session', {
        data: { session_id: sessionId },
    })
}

// ── Health check ───────────────────────────────────────────────
export async function checkHealth(): Promise<{
    status: string
    hf_token_set: boolean
    mode: string
}> {
    const { data } = await api.get('/health')
    return data
}

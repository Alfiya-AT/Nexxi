// src/hooks/useSession.ts
import { useCallback } from 'react'
import toast from 'react-hot-toast'
import { useChatStore } from '@/store/chatStore'
import { clearSession } from '@/services/chatService'

export function useSession() {
    const {
        activeSessionId,
        createNewSession,
        setActiveSession,
        deleteSession,
        sessions,
        clearMessages,
    } = useChatStore()

    const startNewChat = useCallback(() => {
        const id = createNewSession()
        return id
    }, [createNewSession])

    const switchSession = useCallback((sessionId: string) => {
        setActiveSession(sessionId)
    }, [setActiveSession])

    const removeSession = useCallback(async (sessionId: string) => {
        try {
            await clearSession(sessionId)
        } catch {
            // Backend error is non-fatal — still remove locally
        }
        deleteSession(sessionId)
        toast.success('Chat deleted')
    }, [deleteSession])

    const clearCurrentSession = useCallback(async () => {
        if (activeSessionId) {
            try { await clearSession(activeSessionId) } catch { /* ignore */ }
        }
        clearMessages()
        toast.success('Chat cleared')
    }, [activeSessionId, clearMessages])

    return {
        activeSessionId,
        sessions,
        startNewChat,
        switchSession,
        removeSession,
        clearCurrentSession,
    }
}

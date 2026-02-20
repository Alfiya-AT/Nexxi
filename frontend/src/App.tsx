// src/App.tsx
import { Toaster } from 'react-hot-toast'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { useEffect } from 'react'
import { useChatStore } from '@/store/chatStore'

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 2,
            staleTime: 30_000,
            refetchOnWindowFocus: false,
        },
    },
})

function AppInner() {
    const { createNewSession, activeSessionId } = useChatStore()

    // On first mount: if no active session, create one
    useEffect(() => {
        if (!activeSessionId) {
            createNewSession()
        }
    }, []) // eslint-disable-line

    return (
        <div
            className="flex h-screen w-screen overflow-hidden"
            style={{ background: '#0A0A0F' }}
        >
            {/* Background grid + radial glow */}
            <div className="absolute inset-0 bg-grid opacity-40 pointer-events-none" />
            <div
                className="absolute inset-0 pointer-events-none"
                style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(124,58,237,0.12) 0%, transparent 60%)' }}
            />

            {/* ── Sidebar ──────────────────────────────── */}
            <Sidebar />

            {/* ── Main area ─────────────────────────────── */}
            <main className="flex flex-col flex-1 min-w-0 relative">
                <Header />
                <ChatWindow />
            </main>

            {/* ── Toast notifications ───────────────────── */}
            <Toaster
                position="top-right"
                toastOptions={{
                    style: {
                        background: '#12121A',
                        color: '#F8FAFC',
                        border: '1px solid #2D2D3D',
                        borderRadius: '12px',
                        fontSize: '13px',
                    },
                    success: {
                        iconTheme: { primary: '#10B981', secondary: '#0A0A0F' },
                    },
                    error: {
                        iconTheme: { primary: '#EF4444', secondary: '#0A0A0F' },
                    },
                    duration: 3000,
                }}
            />
        </div>
    )
}

export default function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <AppInner />
        </QueryClientProvider>
    )
}

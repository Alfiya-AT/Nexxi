// src/components/layout/Sidebar.tsx
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Plus, Search, MessageSquare, Trash2,
    Settings, X, ChevronRight, Clock
} from 'lucide-react'
import { clsx } from 'clsx'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useSession } from '@/hooks/useSession'
import { useSessionStore } from '@/store/sessionStore'
import { useChatStore } from '@/store/chatStore'
import { formatSessionGroup, truncate } from '@/utils/formatters'

export function Sidebar() {
    const { isSidebarOpen, setSidebarOpen, searchQuery, setSearchQuery } = useSessionStore()
    const { sessions, activeSessionId, startNewChat, switchSession, removeSession } = useSession()
    const { isLoading } = useChatStore()
    const [hoveredId, setHoveredId] = useState<string | null>(null)

    const filtered = sessions.filter(s =>
        s.title.toLowerCase().includes(searchQuery.toLowerCase())
    )

    // Group sessions by date
    const groups = filtered.reduce<Record<string, typeof filtered>>((acc, session) => {
        const label = formatSessionGroup(session.updatedAt)
        if (!acc[label]) acc[label] = []
        acc[label].push(session)
        return acc
    }, {})

    const sidebarContent = (
        <div className="flex flex-col h-full">
            {/* ── Header ────────────────────────────────── */}
            <div className="p-4 border-b border-nexxi-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div
                        className="w-7 h-7 rounded-lg flex items-center justify-center text-white font-bold text-xs"
                        style={{ background: 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)' }}
                    >
                        N
                    </div>
                    <span className="gradient-text font-bold text-sm">Nexxi</span>
                </div>
                <button
                    onClick={() => setSidebarOpen(false)}
                    className="text-nexxi-text-muted hover:text-nexxi-text-primary transition-colors lg:hidden"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* ── New Chat Button ────────────────────────── */}
            <div className="p-3">
                <button
                    onClick={() => { startNewChat(); setSidebarOpen(window.innerWidth >= 1024) }}
                    disabled={isLoading}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm text-white transition-all duration-200 active:scale-95"
                    style={{ background: 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)', boxShadow: '0 0 20px rgba(124,58,237,0.3)' }}
                >
                    <Plus className="w-4 h-4" />
                    New Chat
                </button>
            </div>

            {/* ── Search ────────────────────────────────── */}
            <div className="px-3 pb-3">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-nexxi-text-muted" />
                    <input
                        type="text"
                        placeholder="Search chats…"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-nexxi-bg-tertiary border border-nexxi-border text-nexxi-text-primary placeholder-nexxi-text-muted focus:outline-none focus:border-nexxi-accent transition-colors"
                    />
                </div>
            </div>

            {/* ── Session List ──────────────────────────── */}
            <div className="flex-1 overflow-y-auto px-2 pb-2">
                {Object.keys(groups).length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 gap-3 text-center px-4">
                        <MessageSquare className="w-8 h-8 text-nexxi-text-muted" />
                        <p className="text-nexxi-text-muted text-xs">
                            {searchQuery ? 'No chats match your search' : "No chats yet. Start a conversation!"}
                        </p>
                    </div>
                ) : (
                    Object.entries(groups).map(([groupLabel, groupSessions]) => (
                        <div key={groupLabel} className="mb-3">
                            {/* Group label */}
                            <div className="flex items-center gap-2 px-2 mb-1">
                                <Clock className="w-3 h-3 text-nexxi-text-muted" />
                                <span className="text-[10px] font-semibold text-nexxi-text-muted uppercase tracking-wider">
                                    {groupLabel}
                                </span>
                            </div>
                            {groupSessions.map(session => (
                                <motion.div
                                    key={session.id}
                                    initial={{ opacity: 0, x: -12 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className={clsx(
                                        'sidebar-item group relative',
                                        activeSessionId === session.id && 'active'
                                    )}
                                    onMouseEnter={() => setHoveredId(session.id)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    onClick={() => { switchSession(session.id); setSidebarOpen(window.innerWidth >= 1024) }}
                                >
                                    <MessageSquare className="w-4 h-4 flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-medium truncate">
                                            {truncate(session.title, 30)}
                                        </p>
                                    </div>

                                    {/* Delete button (on hover) */}
                                    <AnimatePresence>
                                        {hoveredId === session.id && (
                                            <motion.button
                                                initial={{ opacity: 0, scale: 0.8 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                exit={{ opacity: 0, scale: 0.8 }}
                                                onClick={e => { e.stopPropagation(); removeSession(session.id) }}
                                                className="p-1 rounded-lg text-nexxi-text-muted hover:text-nexxi-error hover:bg-nexxi-error/10 transition-colors"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </motion.button>
                                        )}
                                    </AnimatePresence>
                                </motion.div>
                            ))}
                        </div>
                    ))
                )}
            </div>

            {/* ── Footer: user profile ──────────────────── */}
            <div className="p-3 border-t border-nexxi-border">
                <div className="flex items-center gap-2 px-2 py-2 rounded-xl hover:bg-nexxi-bg-tertiary transition-colors cursor-pointer">
                    <div className="w-7 h-7 rounded-full bg-nexxi-bg-tertiary border border-nexxi-border flex items-center justify-center text-xs font-semibold text-nexxi-text-secondary flex-shrink-0">
                        U
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-nexxi-text-primary">User</p>
                        <Badge variant="nexxi" className="mt-0.5 text-[9px]">Powered by Nexxi</Badge>
                    </div>
                    <Settings className="w-4 h-4 text-nexxi-text-muted" />
                </div>
            </div>
        </div>
    )

    return (
        <>
            {/* Desktop sidebar */}
            <AnimatePresence>
                {isSidebarOpen && (
                    <motion.aside
                        key="desktop-sidebar"
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 280, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.25, ease: 'easeInOut' }}
                        className="hidden lg:flex flex-col flex-shrink-0 border-r border-nexxi-border overflow-hidden bg-nexxi-bg-secondary"
                        style={{ minHeight: 0 }}
                    >
                        {sidebarContent}
                    </motion.aside>
                )}
            </AnimatePresence>

            {/* Mobile sidebar (overlay) */}
            <AnimatePresence>
                {isSidebarOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setSidebarOpen(false)}
                            className="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
                        />
                        <motion.aside
                            initial={{ x: -300 }}
                            animate={{ x: 0 }}
                            exit={{ x: -300 }}
                            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                            className="lg:hidden fixed left-0 top-0 z-50 h-full w-72 bg-nexxi-bg-secondary border-r border-nexxi-border"
                        >
                            {sidebarContent}
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </>
    )
}

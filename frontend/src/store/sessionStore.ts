// src/store/sessionStore.ts
// Thin wrapper around session-specific UI state
import { create } from 'zustand'

interface SessionStore {
    isSidebarOpen: boolean
    isSettingsOpen: boolean
    searchQuery: string

    toggleSidebar: () => void
    setSidebarOpen: (open: boolean) => void
    toggleSettings: () => void
    setSearchQuery: (q: string) => void
}

export const useSessionStore = create<SessionStore>((set) => ({
    isSidebarOpen: true,
    isSettingsOpen: false,
    searchQuery: '',

    toggleSidebar: () => set((s) => ({ isSidebarOpen: !s.isSidebarOpen })),
    setSidebarOpen: (open) => set({ isSidebarOpen: open }),
    toggleSettings: () => set((s) => ({ isSettingsOpen: !s.isSettingsOpen })),
    setSearchQuery: (q) => set({ searchQuery: q }),
}))

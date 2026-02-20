// src/components/layout/Header.tsx
import { Zap, RotateCcw, Menu } from 'lucide-react'
import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Tooltip } from '@/components/ui/Tooltip'
import { useSession } from '@/hooks/useSession'
import { useSessionStore } from '@/store/sessionStore'

interface HeaderProps {
    modelName?: string
    isOnline?: boolean
}

export function Header({ modelName = 'Mistral 7B', isOnline = true }: HeaderProps) {
    const { clearCurrentSession } = useSession()
    const { toggleSidebar } = useSessionStore()

    return (
        <motion.header
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-nexxi-border"
            style={{ background: 'rgba(10,10,15,0.85)', backdropFilter: 'blur(20px)' }}
        >
            {/* ── Left: hamburger + brand ─────────────── */}
            <div className="flex items-center gap-3">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleSidebar}
                    className="lg:hidden"
                    aria-label="Toggle sidebar"
                >
                    <Menu className="w-5 h-5" />
                </Button>

                {/* Logo + wordmark */}
                <div className="flex items-center gap-2.5">
                    <motion.div
                        animate={{ boxShadow: ['0 0 20px rgba(124,58,237,0.3)', '0 0 35px rgba(124,58,237,0.6)', '0 0 20px rgba(124,58,237,0.3)'] }}
                        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm"
                        style={{ background: 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)' }}
                    >
                        N
                    </motion.div>
                    <div>
                        <h1 className="gradient-text font-bold text-base leading-none tracking-tight">
                            Nexxi
                        </h1>
                        <p className="text-nexxi-text-muted text-[10px] mt-0.5 tracking-wider uppercase">
                            Next-Gen AI
                        </p>
                    </div>
                </div>

                {/* Online status */}
                <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-nexxi-bg-tertiary border border-nexxi-border">
                    <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-nexxi-success animate-pulse' : 'bg-nexxi-error'}`} />
                    <span className="text-xs text-nexxi-text-secondary">
                        {isOnline ? 'Online' : 'Offline'}
                    </span>
                </div>
            </div>

            {/* ── Right: model badge + actions ─────────── */}
            <div className="flex items-center gap-2">
                <Badge variant="nexxi" className="hidden md:flex">
                    <Zap className="w-3 h-3" />
                    {modelName}
                </Badge>

                <Tooltip content="Clear current chat">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={clearCurrentSession}
                        aria-label="Clear chat"
                    >
                        <RotateCcw className="w-4 h-4" />
                    </Button>
                </Tooltip>
            </div>
        </motion.header>
    )
}

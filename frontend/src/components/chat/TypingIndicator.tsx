// src/components/chat/TypingIndicator.tsx
import { motion, AnimatePresence } from 'framer-motion'
import { Avatar } from '@/components/ui/Avatar'

interface TypingIndicatorProps {
    visible: boolean
}

export function TypingIndicator({ visible }: TypingIndicatorProps) {
    return (
        <AnimatePresence>
            {visible && (
                <motion.div
                    initial={{ opacity: 0, y: 12, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 8, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-end gap-3"
                >
                    <Avatar type="nexxi" animate />

                    <div className="flex flex-col gap-1">
                        {/* Animated dots bubble */}
                        <div
                            className="flex items-center gap-1.5 px-4 py-3 rounded-2xl rounded-tl-sm"
                            style={{
                                background: '#1E1E2E',
                                borderLeft: '2px solid #06B6D4',
                            }}
                        >
                            {[0, 1, 2].map(i => (
                                <motion.div
                                    key={i}
                                    className="w-2 h-2 rounded-full"
                                    style={{ background: i === 0 ? '#7C3AED' : i === 1 ? '#9F7AEA' : '#06B6D4' }}
                                    animate={{ y: [0, -8, 0] }}
                                    transition={{
                                        duration: 1.4,
                                        repeat: Infinity,
                                        delay: i * 0.2,
                                        ease: 'easeInOut',
                                    }}
                                />
                            ))}
                        </div>

                        {/* "Nexxi is thinking..." text */}
                        <p className="text-[10px] text-nexxi-text-muted pl-1 animate-pulse">
                            Nexxi is thinking…
                        </p>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    )
}

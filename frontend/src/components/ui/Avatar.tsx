// src/components/ui/Avatar.tsx
import { clsx } from 'clsx'

interface AvatarProps {
    type: 'nexxi' | 'user'
    size?: 'sm' | 'md' | 'lg'
    className?: string
    animate?: boolean
}

export function Avatar({ type, size = 'md', className, animate = false }: AvatarProps) {
    const sizes = {
        sm: 'w-7 h-7 text-xs rounded-lg',
        md: 'w-9 h-9 text-sm rounded-xl',
        lg: 'w-12 h-12 text-base rounded-2xl',
    }

    if (type === 'nexxi') {
        return (
            <div
                className={clsx(
                    sizes[size],
                    'flex-shrink-0 flex items-center justify-center font-bold text-white',
                    animate && 'animate-glow-pulse',
                    className
                )}
                style={{ background: 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)' }}
            >
                N
            </div>
        )
    }

    return (
        <div
            className={clsx(
                sizes[size],
                'flex-shrink-0 flex items-center justify-center font-semibold',
                'bg-nexxi-bg-tertiary border border-nexxi-border text-nexxi-text-secondary',
                className
            )}
        >
            U
        </div>
    )
}

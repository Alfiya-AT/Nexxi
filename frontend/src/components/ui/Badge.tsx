// src/components/ui/Badge.tsx
import { clsx } from 'clsx'

interface BadgeProps {
    children: React.ReactNode
    variant?: 'default' | 'success' | 'warning' | 'error' | 'nexxi'
    className?: string
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
    const variants = {
        default: 'bg-nexxi-bg-tertiary border-nexxi-border text-nexxi-text-secondary',
        success: 'bg-nexxi-success/10 border-nexxi-success/30 text-nexxi-success',
        warning: 'bg-nexxi-warning/10 border-nexxi-warning/30 text-nexxi-warning',
        error: 'bg-nexxi-error/10 border-nexxi-error/30 text-nexxi-error',
        nexxi: 'bg-nexxi-accent/15 border-nexxi-accent/30 text-nexxi-accent',
    }

    return (
        <span className={clsx(
            'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
            variants[variant],
            className
        )}>
            {children}
        </span>
    )
}

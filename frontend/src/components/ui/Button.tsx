// src/components/ui/Button.tsx
import { forwardRef } from 'react'
import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'sm' | 'md' | 'lg' | 'icon'
    loading?: boolean
    children: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({
    variant = 'secondary',
    size = 'md',
    loading = false,
    children,
    className,
    disabled,
    ...props
}, ref) => {
    const base = 'inline-flex items-center justify-center gap-2 font-medium rounded-xl transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-nexxi-accent select-none'

    const variants = {
        primary: 'btn-nexxi',
        secondary: 'bg-nexxi-bg-tertiary border border-nexxi-border text-nexxi-text-secondary hover:text-nexxi-text-primary hover:border-nexxi-border-light hover:bg-nexxi-bg-secondary',
        ghost: 'text-nexxi-text-secondary hover:text-nexxi-text-primary hover:bg-nexxi-bg-tertiary',
        danger: 'bg-nexxi-error/10 border border-nexxi-error/30 text-nexxi-error hover:bg-nexxi-error/20',
    }

    const sizes = {
        sm: 'px-3 py-1.5 text-xs',
        md: 'px-4 py-2 text-sm',
        lg: 'px-5 py-2.5 text-base',
        icon: 'w-9 h-9 p-0',
    }

    return (
        <button
            ref={ref}
            disabled={disabled || loading}
            className={clsx(base, variants[variant], sizes[size], {
                'opacity-40 cursor-not-allowed': disabled || loading,
            }, className)}
            {...props}
        >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : children}
        </button>
    )
})

Button.displayName = 'Button'

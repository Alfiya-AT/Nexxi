// src/components/ui/Tooltip.tsx
import { useState, useRef } from 'react'
import { clsx } from 'clsx'

interface TooltipProps {
    content: string
    children: React.ReactElement
    position?: 'top' | 'bottom' | 'left' | 'right'
}

export function Tooltip({ content, children, position = 'top' }: TooltipProps) {
    const [visible, setVisible] = useState(false)

    const positionClasses = {
        top: '-top-8 left-1/2 -translate-x-1/2',
        bottom: '-bottom-8 left-1/2 -translate-x-1/2',
        left: 'top-1/2 -translate-y-1/2 -left-2 -translate-x-full',
        right: 'top-1/2 -translate-y-1/2 -right-2 translate-x-full',
    }

    return (
        <div
            className="relative inline-flex"
            onMouseEnter={() => setVisible(true)}
            onMouseLeave={() => setVisible(false)}
        >
            {children}
            {visible && (
                <div className={clsx(
                    'absolute z-50 px-2 py-1 text-xs font-medium whitespace-nowrap rounded-lg pointer-events-none',
                    'bg-nexxi-bg-tertiary border border-nexxi-border text-nexxi-text-primary shadow-card',
                    positionClasses[position],
                    'animate-fade-in'
                )}>
                    {content}
                </div>
            )}
        </div>
    )
}

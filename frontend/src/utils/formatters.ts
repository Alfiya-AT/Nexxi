// src/utils/formatters.ts
import { formatDistanceToNow, format, isToday, isYesterday } from 'date-fns'

/** Format a date as "2m ago", "1h ago", etc. */
export function formatRelativeTime(date: Date | string): string {
    const d = typeof date === 'string' ? new Date(date) : date
    return formatDistanceToNow(d, { addSuffix: true })
}

/** Format message timestamp: "12:34 PM" */
export function formatMessageTime(date: Date | string): string {
    const d = typeof date === 'string' ? new Date(date) : date
    return format(d, 'h:mm a')
}

/** Format session group label: "Today", "Yesterday", "Jan 15" */
export function formatSessionGroup(date: Date | string): string {
    const d = typeof date === 'string' ? new Date(date) : date
    if (isToday(d)) return 'Today'
    if (isYesterday(d)) return 'Yesterday'
    return format(d, 'MMM d')
}

/** Truncate text with ellipsis */
export function truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text
    return text.slice(0, maxLength).trimEnd() + '…'
}

/** Format file size: "1.2 MB", "345 KB" */
export function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Extract session title from first message */
export function extractSessionTitle(firstMessage: string): string {
    return truncate(firstMessage, 42)
}

/** Format token count */
export function formatTokens(count: number): string {
    if (count < 1000) return `${count} tokens`
    return `${(count / 1000).toFixed(1)}k tokens`
}

/** Format response latency */
export function formatLatency(ms: number): string {
    if (ms < 1000) return `${ms.toFixed(0)}ms`
    return `${(ms / 1000).toFixed(1)}s`
}

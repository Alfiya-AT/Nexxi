// src/components/chat/ChatBubble.tsx
import { useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check, AlertCircle, FileText, Image } from 'lucide-react'
import { clsx } from 'clsx'
import { Avatar } from '@/components/ui/Avatar'
import { Tooltip } from '@/components/ui/Tooltip'
import { formatMessageTime, formatLatency, formatTokens } from '@/utils/formatters'
import type { Message } from '@/types/chat.types'

interface ChatBubbleProps {
    message: Message
    index: number
}

export function ChatBubble({ message, index }: ChatBubbleProps) {
    const [copied, setCopied] = useState(false)
    const isUser = message.role === 'user'

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(message.content)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch { /* ignore */ }
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.3, delay: Math.min(index * 0.05, 0.3) }}
            className={clsx('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}
        >
            {/* Avatar */}
            <Avatar type={isUser ? 'user' : 'nexxi'} animate={!isUser} />

            {/* Bubble + meta */}
            <div className={clsx('flex flex-col max-w-[75%]', isUser ? 'items-end' : 'items-start')}>

                {/* File attachments */}
                {message.files && message.files.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-2">
                        {message.files.map(file => (
                            <div
                                key={file.id}
                                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-nexxi-bg-tertiary border border-nexxi-border"
                            >
                                {file.type.startsWith('image/') ? (
                                    <Image className="w-3.5 h-3.5 text-nexxi-cyan" />
                                ) : (
                                    <FileText className="w-3.5 h-3.5 text-nexxi-accent" />
                                )}
                                <span className="text-xs text-nexxi-text-secondary">{file.name}</span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Message bubble */}
                <div className={clsx('group relative', isUser ? 'bubble-user' : 'bubble-bot')}>

                    {/* Error state */}
                    {message.error ? (
                        <div className="flex items-center gap-2 text-nexxi-error">
                            <AlertCircle className="w-4 h-4 flex-shrink-0" />
                            <span className="text-sm text-nexxi-text-secondary">
                                {message.content || 'Something went wrong. Please try again.'}
                            </span>
                        </div>
                    ) : (
                        <div className="nexxi-prose">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    code({ node, className, children, ...props }) {
                                        const match = /language-(\w+)/.exec(className || '')
                                        const isBlock = !!match
                                        return isBlock ? (
                                            <SyntaxHighlighter
                                                style={oneDark as Record<string, React.CSSProperties>}
                                                language={match[1]}
                                                PreTag="div"
                                                customStyle={{
                                                    borderRadius: '10px',
                                                    fontSize: '12px',
                                                    margin: '8px 0',
                                                    background: '#0A0A0F',
                                                    border: '1px solid #2D2D3D',
                                                }}
                                            >
                                                {String(children).replace(/\n$/, '')}
                                            </SyntaxHighlighter>
                                        ) : (
                                            <code className={className} {...props}>
                                                {children}
                                            </code>
                                        )
                                    },
                                }}
                            >
                                {message.content}
                            </ReactMarkdown>
                            {/* Streaming cursor */}
                            {message.isStreaming && (
                                <span className="inline-block w-0.5 h-4 bg-nexxi-cyan ml-0.5 animate-pulse align-middle" />
                            )}
                        </div>
                    )}

                    {/* Copy button (hover) */}
                    {message.content && !message.isStreaming && (
                        <Tooltip content={copied ? 'Copied!' : 'Copy message'} position={isUser ? 'left' : 'right'}>
                            <button
                                onClick={handleCopy}
                                className={clsx(
                                    'absolute -top-2 p-1.5 rounded-lg border transition-all duration-200',
                                    'opacity-0 group-hover:opacity-100',
                                    isUser ? '-left-10' : '-right-10',
                                    'bg-nexxi-bg-secondary border-nexxi-border text-nexxi-text-muted hover:text-nexxi-text-primary'
                                )}
                            >
                                {copied
                                    ? <Check className="w-3.5 h-3.5 text-nexxi-success" />
                                    : <Copy className="w-3.5 h-3.5" />
                                }
                            </button>
                        </Tooltip>
                    )}
                </div>

                {/* Metadata row */}
                <div className={clsx('flex items-center gap-2 mt-1.5', isUser ? 'flex-row-reverse' : 'flex-row')}>
                    <span className="text-[10px] text-nexxi-text-muted">
                        {formatMessageTime(message.timestamp)}
                    </span>
                    {!isUser && message.tokensUsed && (
                        <>
                            <span className="text-nexxi-text-muted text-[10px]">·</span>
                            <span className="text-[10px] text-nexxi-text-muted">
                                {formatTokens(message.tokensUsed)}
                            </span>
                        </>
                    )}
                    {!isUser && message.responseTimeMs && (
                        <>
                            <span className="text-nexxi-text-muted text-[10px]">·</span>
                            <span className="text-[10px] text-nexxi-text-muted">
                                {formatLatency(message.responseTimeMs)}
                            </span>
                        </>
                    )}
                </div>
            </div>
        </motion.div>
    )
}

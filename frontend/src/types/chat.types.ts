// src/types/chat.types.ts

export interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    files?: UploadedFile[]
    isStreaming?: boolean
    error?: boolean
    tokensUsed?: number
    responseTimeMs?: number
}

export interface Session {
    id: string
    title: string
    createdAt: Date
    updatedAt: Date
    messageCount: number
    preview?: string   // Last message preview
}

export interface UploadedFile {
    id: string
    name: string
    size: number
    type: string
    url: string
    file?: File        // Original File object for upload
}

export interface ChatRequest {
    session_id?: string
    message: string
    stream?: boolean
    files?: string[]
}

export interface ChatResponse {
    session_id: string
    message: string
    model: string
    tokens_used: number
    response_time_ms: number
    timestamp: string
}

export interface StreamChunk {
    session_id: string
    delta: string
    finished: boolean
}

export interface ErrorResponse {
    error: string
    detail: string
    timestamp: string
}

export type MessageRole = 'user' | 'assistant' | 'system'

export type VoiceState = 'idle' | 'listening' | 'processing' | 'error'

export type FileUploadStatus = 'idle' | 'uploading' | 'done' | 'error'

export interface FileWithPreview extends File {
    preview?: string
}

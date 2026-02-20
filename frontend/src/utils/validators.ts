// src/utils/validators.ts

const MAX_MESSAGE_LENGTH = 1000
const ALLOWED_FILE_TYPES = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg', 'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
const ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.txt', '.docx']
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  // 10 MB
const MAX_FILE_COUNT = 3

export interface ValidationResult {
    valid: boolean
    error?: string
}

/** Validate a chat message */
export function validateMessage(text: string): ValidationResult {
    if (!text || text.trim().length === 0) {
        return { valid: false, error: 'Message cannot be empty.' }
    }
    if (text.length > MAX_MESSAGE_LENGTH) {
        return { valid: false, error: `Message exceeds ${MAX_MESSAGE_LENGTH} characters.` }
    }
    return { valid: true }
}

/** Validate a single uploaded file */
export function validateFile(file: File): ValidationResult {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()

    if (!ALLOWED_EXTENSIONS.includes(ext) && !ALLOWED_FILE_TYPES.includes(file.type)) {
        return {
            valid: false,
            error: `File type "${ext}" is not supported. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`,
        }
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
        return {
            valid: false,
            error: `File "${file.name}" exceeds 10MB limit.`,
        }
    }
    return { valid: true }
}

/** Validate a batch of files */
export function validateFiles(files: File[]): ValidationResult {
    if (files.length > MAX_FILE_COUNT) {
        return { valid: false, error: `Maximum ${MAX_FILE_COUNT} files at a time.` }
    }
    for (const file of files) {
        const result = validateFile(file)
        if (!result.valid) return result
    }
    return { valid: true }
}

/** Check if browser supports Web Speech API */
export function isSpeechRecognitionSupported(): boolean {
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
}

/** Check if browser supports clipboard write */
export function isClipboardSupported(): boolean {
    return !!navigator.clipboard?.writeText
}

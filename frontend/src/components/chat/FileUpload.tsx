// src/components/chat/FileUpload.tsx
import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, X, FileText, Image, File } from 'lucide-react'
import { clsx } from 'clsx'
import { Tooltip } from '@/components/ui/Tooltip'
import { formatFileSize } from '@/utils/formatters'
import type { UploadedFile } from '@/types/chat.types'

interface FileUploadProps {
    uploadedFiles: UploadedFile[]
    onFiles: (files: File[]) => void
    onRemove: (id: string) => void
    disabled?: boolean
}

function FileIcon({ type }: { type: string }) {
    if (type.startsWith('image/')) return <Image className="w-4 h-4 text-nexxi-cyan" />
    if (type === 'application/pdf') return <FileText className="w-4 h-4 text-nexxi-error" />
    return <File className="w-4 h-4 text-nexxi-accent" />
}

export function FileUpload({ uploadedFiles, onFiles, onRemove, disabled }: FileUploadProps) {
    const onDrop = useCallback((accepted: File[]) => {
        onFiles(accepted)
    }, [onFiles])

    const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
        onDrop,
        disabled,
        noClick: true,     // We control click manually
        multiple: true,
        accept: {
            'image/*': ['.png', '.jpg', '.jpeg'],
            'application/pdf': ['.pdf'],
            'text/plain': ['.txt'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        },
        maxSize: 10 * 1024 * 1024,  // 10 MB
        maxFiles: 3,
    })

    return (
        <div>
            {/* Trigger button */}
            <Tooltip content="Attach files">
                <button
                    type="button"
                    onClick={open}
                    disabled={disabled || uploadedFiles.length >= 3}
                    className={clsx(
                        'p-2 rounded-xl transition-all duration-200',
                        'text-nexxi-text-muted hover:text-nexxi-text-primary hover:bg-nexxi-bg-tertiary',
                        (disabled || uploadedFiles.length >= 3) && 'opacity-40 cursor-not-allowed'
                    )}
                    aria-label="Attach file"
                >
                    <Upload className="w-5 h-5" />
                </button>
            </Tooltip>

            {/* Drag overlay */}
            <div {...getRootProps()}>
                <input {...getInputProps()} />
                <AnimatePresence>
                    {isDragActive && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-50 flex items-center justify-center"
                            style={{ background: 'rgba(10,10,15,0.85)', backdropFilter: 'blur(8px)' }}
                        >
                            <motion.div
                                initial={{ scale: 0.9 }}
                                animate={{ scale: 1 }}
                                className="flex flex-col items-center gap-4 p-12 rounded-2xl border-2 border-dashed border-nexxi-accent"
                                style={{ background: 'rgba(124,58,237,0.08)' }}
                            >
                                <Upload className="w-12 h-12 text-nexxi-accent animate-float" />
                                <p className="gradient-text font-bold text-xl">Drop files here</p>
                                <p className="text-nexxi-text-muted text-sm">
                                    PDF, PNG, JPG, TXT, DOCX — max 10MB each
                                </p>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* File previews (rendered inline above input) */}
            <AnimatePresence>
                {uploadedFiles.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="absolute bottom-full left-0 right-0 mb-2 px-4"
                    >
                        <div className="flex gap-2 flex-wrap p-3 rounded-xl glass border-nexxi-border">
                            {uploadedFiles.map(file => (
                                <motion.div
                                    key={file.id}
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-nexxi-bg-tertiary border border-nexxi-border"
                                >
                                    {file.type.startsWith('image/') && file.url ? (
                                        <img src={file.url} alt={file.name} className="w-5 h-5 rounded object-cover" />
                                    ) : (
                                        <FileIcon type={file.type} />
                                    )}
                                    <span className="text-xs text-nexxi-text-secondary max-w-[100px] truncate">
                                        {file.name}
                                    </span>
                                    <span className="text-[10px] text-nexxi-text-muted">
                                        {formatFileSize(file.size)}
                                    </span>
                                    <button
                                        onClick={() => onRemove(file.id)}
                                        className="text-nexxi-text-muted hover:text-nexxi-error transition-colors"
                                    >
                                        <X className="w-3 h-3" />
                                    </button>
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

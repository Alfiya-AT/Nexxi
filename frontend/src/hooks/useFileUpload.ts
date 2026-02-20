// src/hooks/useFileUpload.ts
import { useState, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import toast from 'react-hot-toast'
import { validateFiles } from '@/utils/validators'
import { formatFileSize } from '@/utils/formatters'
import type { UploadedFile } from '@/types/chat.types'

interface UseFileUploadReturn {
    uploadedFiles: UploadedFile[]
    isDragging: boolean
    handleFiles: (files: File[]) => void
    removeFile: (id: string) => void
    clearFiles: () => void
    setIsDragging: (v: boolean) => void
}

export function useFileUpload(): UseFileUploadReturn {
    const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
    const [isDragging, setIsDragging] = useState(false)

    const handleFiles = useCallback((rawFiles: File[]) => {
        // Client-side validation
        const validation = validateFiles(rawFiles)
        if (!validation.valid) {
            toast.error(validation.error ?? 'Invalid file(s).')
            return
        }

        const newFiles: UploadedFile[] = rawFiles.map(file => ({
            id: uuidv4(),
            name: file.name,
            size: file.size,
            type: file.type,
            // Create object URL for preview rendering
            url: URL.createObjectURL(file),
            file,
        }))

        setUploadedFiles(prev => {
            const combined = [...prev, ...newFiles]
            if (combined.length > 3) {
                toast.error('Maximum 3 files at a time.')
                return prev
            }
            return combined
        })

        toast.success(
            newFiles.length === 1
                ? `📎 ${newFiles[0].name} (${formatFileSize(newFiles[0].size)}) attached`
                : `📎 ${newFiles.length} files attached`
        )
    }, [])

    const removeFile = useCallback((id: string) => {
        setUploadedFiles(prev => {
            const file = prev.find(f => f.id === id)
            if (file?.url) URL.revokeObjectURL(file.url)  // Clean up object URL
            return prev.filter(f => f.id !== id)
        })
    }, [])

    const clearFiles = useCallback(() => {
        setUploadedFiles(prev => {
            prev.forEach(f => { if (f.url) URL.revokeObjectURL(f.url) })
            return []
        })
    }, [])

    return {
        uploadedFiles,
        isDragging,
        handleFiles,
        removeFile,
        clearFiles,
        setIsDragging,
    }
}

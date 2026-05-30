import http from '@/utils/request'

export type UploadedImage = {
    object_key: string
    content_type: string
    extension: string
    size: number
    original_filename: string | null
    url?: string
    url_expires_at?: number
}

export type DeleteImageData = {
    object_key: string
}

export type PresignImagesData = {
    urls: Record<string, string>
    expires_at: number
}

export function uploadImage(file: File): Promise<UploadedImage> {
    const formData = new FormData()

    formData.append('file', file)

    return http.uploadForm<UploadedImage>('/upload/image', formData)
}

export function presignImages(objectKeys: string[]): Promise<PresignImagesData> {
    return http.post<PresignImagesData>('/upload/image/presign', {
        object_keys: objectKeys,
    })
}

export function deleteImage(objectKey: string): Promise<DeleteImageData> {
    return http.delete<DeleteImageData>('/upload/image', {
        body: {
            object_key: objectKey,
        },
    })
}

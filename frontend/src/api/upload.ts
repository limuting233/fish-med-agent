import http from '@/utils/request'

export type UploadedImage = {
    object_key: string
    content_type: string
    extension: string
    size: number
    original_filename: string | null
}

export type DeleteImageData = {
    object_key: string
}

export function uploadImage(file: File): Promise<UploadedImage> {
    const formData = new FormData()

    formData.append('file', file)

    return http.uploadForm<UploadedImage>('/upload/image', formData)
}

export function deleteImage(objectKey: string): Promise<DeleteImageData> {
    return http.delete<DeleteImageData>('/upload/image', {
        body: {
            object_key: objectKey,
        },
    })
}

import apiClient from './client'
import type { ImageExtractionResult, ImageUploadResult } from './types'

export async function uploadImage(file: File): Promise<ImageUploadResult> {
  const formData = new FormData()
  formData.append('file', file, file.name || 'image.jpg')

  const { data } = await apiClient.post<ImageUploadResult>('/uploads/images', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function extractQuestions(
  imagePath: string,
  subject?: string,
): Promise<ImageExtractionResult> {
  const { data } = await apiClient.post<ImageExtractionResult>(
    '/questions/from-image',
    {
      image_path: imagePath,
      ...(subject?.trim() ? { subject: subject.trim() } : {}),
    },
    { timeout: 180_000 },
  )
  return data
}

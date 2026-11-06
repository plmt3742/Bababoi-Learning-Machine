export const MAX_SELECT_BYTES = 20 * 1024 * 1024
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
export const MAX_IMAGE_EDGE = 2000
export const TARGET_IMAGE_BYTES = 5 * 1024 * 1024

export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const
export const IMAGE_ACCEPT_ATTRIBUTE = ACCEPTED_IMAGE_TYPES.join(',')

export type AcceptedImageMime = (typeof ACCEPTED_IMAGE_TYPES)[number]

export interface PreparedImage {
  file: File
  width: number
  height: number
}

export interface PixelCropRect {
  x: number
  y: number
  width: number
  height: number
}

function isAcceptedMime(value: string): value is AcceptedImageMime {
  return ACCEPTED_IMAGE_TYPES.some((mime) => mime === value)
}

function extensionFor(mime: AcceptedImageMime): string {
  if (mime === 'image/png') return 'png'
  if (mime === 'image/webp') return 'webp'
  return 'jpg'
}

function inferMimeFromName(name: string): AcceptedImageMime | null {
  const extension = name.split('.').pop()?.toLowerCase()
  if (extension === 'png') return 'image/png'
  if (extension === 'webp') return 'image/webp'
  if (extension === 'jpg' || extension === 'jpeg') return 'image/jpeg'
  return null
}

export function normalizeImageMime(type: string, name = ''): AcceptedImageMime {
  if (isAcceptedMime(type)) return type
  return inferMimeFromName(name) ?? 'image/jpeg'
}

export function isAcceptedImageFile(file: File): boolean {
  return isAcceptedMime(file.type) || (file.type === '' && inferMimeFromName(file.name) !== null)
}

export function validateImageFile(file: File): string | null {
  if (!isAcceptedImageFile(file)) {
    return '仅支持 JPEG、PNG 或 WebP 图片'
  }
  if (file.size === 0) {
    return '图片文件为空，请重新选择'
  }
  if (file.size > MAX_SELECT_BYTES) {
    return `图片不能超过 20MB（当前 ${formatFileSize(file.size)}）`
  }
  return null
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function loadImageFromFile(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file)
    const image = new Image()

    image.onload = () => {
      URL.revokeObjectURL(objectUrl)
      resolve(image)
    }
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('无法读取这张图片，请换一张重试'))
    }
    image.src = objectUrl
  })
}

function canvasToBlob(
  canvas: HTMLCanvasElement,
  mime: AcceptedImageMime,
  quality: number,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob)
        else reject(new Error('图片编码失败，请换一张重试'))
      },
      mime,
      quality,
    )
  })
}

function rasterize(
  source: CanvasImageSource,
  width: number,
  height: number,
  mime: AcceptedImageMime,
  quality: number,
): Promise<Blob> {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height

  const context = canvas.getContext('2d')
  if (!context) throw new Error('当前浏览器无法处理图片，请换一个浏览器')

  if (mime === 'image/jpeg') {
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, width, height)
  }

  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(source, 0, 0, width, height)

  return canvasToBlob(canvas, mime, quality)
}

function outputFileName(name: string, mime: AcceptedImageMime): string {
  const base =
    name
      .replace(/\.[^.]+$/, '')
      .trim()
      .slice(0, 60) || 'image'
  return `${base}.${extensionFor(mime)}`
}

export async function compressImageFile(file: File): Promise<PreparedImage> {
  const image = await loadImageFromFile(file)
  const mime = normalizeImageMime(file.type, file.name)
  const fitScale = Math.min(1, MAX_IMAGE_EDGE / Math.max(image.naturalWidth, image.naturalHeight))

  let width = Math.max(1, Math.round(image.naturalWidth * fitScale))
  let height = Math.max(1, Math.round(image.naturalHeight * fitScale))
  let quality = 0.9
  let blob = await rasterize(image, width, height, mime, quality)

  for (let attempt = 0; attempt < 12 && blob.size > TARGET_IMAGE_BYTES; attempt += 1) {
    if (mime !== 'image/png' && quality > 0.62) {
      quality = Math.max(0.6, quality - 0.08)
    } else {
      const nextWidth = Math.max(1, Math.round(width * 0.82))
      const nextHeight = Math.max(1, Math.round(height * 0.82))
      if (nextWidth === width && nextHeight === height) break
      width = nextWidth
      height = nextHeight
    }

    blob = await rasterize(image, width, height, mime, quality)
  }

  const outputMime = isAcceptedMime(blob.type) ? blob.type : mime
  return {
    file: new File([blob], outputFileName(file.name, outputMime), {
      type: blob.type || outputMime,
      lastModified: Date.now(),
    }),
    width,
    height,
  }
}

function normalizeRotation(value: number): number {
  const snapped = Math.round(value / 90) * 90
  return ((snapped % 360) + 360) % 360
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

export async function cropRotateImage(
  file: File,
  rotation: number,
  crop: PixelCropRect,
): Promise<File> {
  const image = await loadImageFromFile(file)
  const angle = normalizeRotation(rotation)
  const swapSides = angle === 90 || angle === 270
  const rotatedWidth = swapSides ? image.naturalHeight : image.naturalWidth
  const rotatedHeight = swapSides ? image.naturalWidth : image.naturalHeight

  const rotated = document.createElement('canvas')
  rotated.width = rotatedWidth
  rotated.height = rotatedHeight

  const rotatedContext = rotated.getContext('2d')
  if (!rotatedContext) throw new Error('当前浏览器无法处理图片，请换一个浏览器')

  rotatedContext.translate(rotatedWidth / 2, rotatedHeight / 2)
  rotatedContext.rotate((angle * Math.PI) / 180)
  rotatedContext.drawImage(image, -image.naturalWidth / 2, -image.naturalHeight / 2)

  const x = clamp(Math.round(crop.x), 0, Math.max(0, rotatedWidth - 1))
  const y = clamp(Math.round(crop.y), 0, Math.max(0, rotatedHeight - 1))
  const cropWidth = clamp(Math.round(crop.width), 1, rotatedWidth - x)
  const cropHeight = clamp(Math.round(crop.height), 1, rotatedHeight - y)
  const outputScale = Math.min(1, MAX_IMAGE_EDGE / Math.max(cropWidth, cropHeight))
  const outputWidth = Math.max(1, Math.round(cropWidth * outputScale))
  const outputHeight = Math.max(1, Math.round(cropHeight * outputScale))

  const mime = normalizeImageMime(file.type, file.name)
  const output = document.createElement('canvas')
  output.width = outputWidth
  output.height = outputHeight

  const outputContext = output.getContext('2d')
  if (!outputContext) throw new Error('当前浏览器无法处理图片，请换一个浏览器')

  if (mime === 'image/jpeg') {
    outputContext.fillStyle = '#ffffff'
    outputContext.fillRect(0, 0, outputWidth, outputHeight)
  }

  outputContext.imageSmoothingEnabled = true
  outputContext.imageSmoothingQuality = 'high'
  outputContext.drawImage(rotated, x, y, cropWidth, cropHeight, 0, 0, outputWidth, outputHeight)

  const blob = await canvasToBlob(output, mime, 0.92)
  return new File([blob], outputFileName(file.name, mime), {
    type: blob.type || mime,
    lastModified: Date.now(),
  })
}

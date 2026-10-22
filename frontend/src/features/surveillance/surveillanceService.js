import apiClient from '../../services/apiClient'
import { ENDPOINTS } from '../../services/endpoints'

export async function detectImage(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post(ENDPOINTS.detectImage, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

export async function detectVideo(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post(ENDPOINTS.detectVideo, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
  return data
}

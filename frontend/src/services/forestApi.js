import apiClient from './apiClient'
import { ENDPOINTS } from './endpoints'

export async function fetchHealth() {
  const { data } = await apiClient.get(ENDPOINTS.health)
  return data
}

export async function fetchDashboardSummary() {
  const { data } = await apiClient.get(ENDPOINTS.dashboardSummary)
  return data
}

export async function fetchIncidents(params = {}) {
  const { data } = await apiClient.get(ENDPOINTS.incidents, { params })
  return data
}

export async function fetchIncident(id) {
  const { data } = await apiClient.get(ENDPOINTS.incident(id))
  return data
}

export async function fetchIncidentImages(id) {
  const { data } = await apiClient.get(ENDPOINTS.incidentImages(id))
  return data
}

export async function patchIncident(id, body) {
  const { data } = await apiClient.patch(ENDPOINTS.incident(id), body)
  return data
}

export async function fetchPoles() {
  const { data } = await apiClient.get(ENDPOINTS.poles)
  return data
}

export async function fetchDeviceData(poleId) {
  const { data } = await apiClient.get(ENDPOINTS.device(poleId))
  return data
}

export async function fetchCameras() {
  const { data } = await apiClient.get(ENDPOINTS.cameras)
  return data
}

export async function fetchMonitorStatus() {
  const { data } = await apiClient.get(ENDPOINTS.monitorStatus)
  return data
}

export async function startMonitor(cameraIndex, cameraId) {
  const { data } = await apiClient.post(ENDPOINTS.monitorStart, null, {
    params: { camera_index: cameraIndex, camera_id: cameraId },
  })
  return data
}

export async function stopMonitor() {
  const { data } = await apiClient.post(ENDPOINTS.monitorStop)
  return data
}

export async function fetchAnalytics(days = 7) {
  const { data } = await apiClient.get(ENDPOINTS.analyticsDetections, { params: { days } })
  return data
}

export async function fetchModelMetrics() {
  const { data } = await apiClient.get(ENDPOINTS.modelMetrics)
  return data
}

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

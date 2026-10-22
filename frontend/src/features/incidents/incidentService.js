import apiClient from '../../services/apiClient'
import { ENDPOINTS } from '../../services/endpoints'

export async function fetchIncidents(params = {}) {
  const { data } = await apiClient.get(ENDPOINTS.incidents, { params })
  return data
}

export async function fetchIncident(id) {
  const { data } = await apiClient.get(ENDPOINTS.incident(id))
  return data
}

export async function patchIncident(id, body) {
  const { data } = await apiClient.patch(ENDPOINTS.incident(id), body)
  return data
}

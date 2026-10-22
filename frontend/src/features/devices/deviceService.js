import apiClient from '../../services/apiClient'
import { ENDPOINTS } from '../../services/endpoints'

export async function fetchDevices() {
  const { data } = await apiClient.get(ENDPOINTS.devices)
  return data
}

export async function fetchDevice(poleId) {
  const { data } = await apiClient.get(ENDPOINTS.device(poleId))
  return data
}

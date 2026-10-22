import apiClient from '../../services/apiClient'
import { ENDPOINTS } from '../../services/endpoints'

export async function fetchHealth() {
  const { data } = await apiClient.get(ENDPOINTS.health)
  return data
}

export async function fetchDashboardSummary() {
  const { data } = await apiClient.get(ENDPOINTS.dashboardSummary)
  return data
}

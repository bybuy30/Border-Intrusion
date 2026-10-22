import { fetchDeviceData, fetchPoles } from '../../services/forestApi'

export async function fetchDevices() {
  const items = await fetchPoles()
  return { items, total: items.length }
}

export const fetchDevice = fetchDeviceData

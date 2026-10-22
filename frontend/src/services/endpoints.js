// All API endpoint paths in one place — import from here, never hardcode URLs

export const ENDPOINTS = {
  health:              '/api/health',
  dashboardSummary:    '/api/dashboard/summary',
  incidents:           '/api/incidents',
  incident:            (id) => `/api/incidents/${id}`,
  analyticsDetections: '/api/analytics/detections',
  devices:             '/api/devices',
  device:              (poleId) => `/api/devices/${poleId}`,
  poles:               '/api/poles',
  cameras:             '/api/cameras/discover',
  monitorStatus:       '/api/monitor/status',
  monitorStart:        '/api/monitor/start',
  monitorStop:         '/api/monitor/stop',
  monitorStream:       '/api/monitor/stream',
  incidentImages:      (id) => `/api/incidents/${id}/images`,
  modelMetrics:        '/api/model/metrics',
  detectImage:         '/api/detect/image',
  detectVideo:         '/api/detect/video',
}

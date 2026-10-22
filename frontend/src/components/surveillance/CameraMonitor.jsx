import React, { useEffect, useState } from 'react'
import { Camera, Circle, Play, RefreshCw, Square, VideoOff } from 'lucide-react'
import useMonitor from '../../hooks/useMonitor'
import { apiUrl } from '../../services/apiClient'
import { ENDPOINTS } from '../../services/endpoints'
import { formatDate } from '../../utils/formatDate'
import ErrorState from '../common/ErrorState'

export default function CameraMonitor({ onStatusChange }) {
  const monitor = useMonitor()
  const [streamFailed, setStreamFailed] = useState(false)
  useEffect(() => {
    if (onStatusChange) onStatusChange(monitor.status)
  }, [monitor.status, onStatusChange])
  useEffect(() => { setStreamFailed(false) }, [monitor.streamKey])
  const running = Boolean(monitor.status?.running)
  const connected = Boolean(monitor.status?.connected)
  const imageUrl = `${apiUrl(ENDPOINTS.monitorStream)}?t=${monitor.streamKey}`

  return (
    <section className="panel overflow-hidden">
      <div className="panel-header flex-wrap gap-3">
        <div>
          <h2 className="panel-title">Live camera monitoring</h2>
          <p className="text-[11px] text-slate-500 mt-1">
            {monitor.status?.camera_id || 'No camera selected'}
            {monitor.status?.camera_index != null && ` · index ${monitor.status.camera_index}`}
          </p>
        </div>
        <div className={`badge border ${connected ? 'bg-forest-950 text-forest-300 border-forest-700' : running ? 'bg-amber-950 text-amber-300 border-amber-800' : 'bg-surface-700 text-slate-400 border-forest-800'}`}>
          <Circle className={`w-2 h-2 fill-current ${connected ? 'text-forest-400' : running ? 'text-amber-400' : 'text-slate-500'}`} />
          {connected ? 'Connected' : running ? 'Connecting' : 'Disconnected'}
        </div>
      </div>

      <div className="relative aspect-video bg-black/50 flex items-center justify-center">
        {running && connected && !streamFailed ? (
          <img
            key={monitor.streamKey}
            src={imageUrl}
            alt="Annotated live camera feed"
            className="w-full h-full object-contain"
            onLoad={() => setStreamFailed(false)}
            onError={() => setStreamFailed(true)}
          />
        ) : (
          <div className="px-6 py-8 text-center">
            {running && !connected ? (
              <>
                <Camera className="w-8 h-8 text-amber-400 mx-auto mb-3 animate-pulse" />
                <p className="text-sm text-slate-200">Connecting to camera…</p>
              </>
            ) : streamFailed ? (
              <ErrorState message="The live video stream disconnected. Check camera and backend status." onRetry={() => { setStreamFailed(false); monitor.refreshStatus() }} />
            ) : (
              <>
                <VideoOff className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                <p className="text-sm text-slate-300">Camera monitoring is stopped</p>
                <p className="text-xs text-slate-500 mt-1">Start monitoring to display the annotated live feed.</p>
              </>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4">
        <label className="flex-1 min-w-0">
          <span className="block text-[11px] text-slate-500 mb-1">Available cameras</span>
          <select
            className="select"
            value={monitor.selectedIndex}
            disabled={running || monitor.loadingCameras || !monitor.cameras.length}
            onChange={(event) => monitor.setSelectedIndex(event.target.value)}
          >
            {monitor.loadingCameras && <option value="">Searching for cameras…</option>}
            {!monitor.loadingCameras && !monitor.cameras.length && <option value="">No cameras found</option>}
            {monitor.cameras.map((camera) => (
              <option key={camera.camera_index} value={camera.camera_index}>
                {camera.camera_id} · camera index {camera.camera_index}
              </option>
            ))}
          </select>
        </label>
        <div className="flex gap-2 sm:self-end">
          <button
            className="btn-secondary"
            onClick={monitor.discover}
            disabled={monitor.loadingCameras || running || monitor.busy}
            type="button"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${monitor.loadingCameras ? 'animate-spin' : ''}`} />
            Discover
          </button>
          {running ? (
            <button className="btn-danger" onClick={monitor.stop} disabled={monitor.busy} type="button">
              <Square className="w-3.5 h-3.5" /> Stop monitoring
            </button>
          ) : (
            <button className="btn-primary" onClick={monitor.start} disabled={monitor.busy || !monitor.cameras.length} type="button">
              <Play className="w-3.5 h-3.5" /> Start monitoring
            </button>
          )}
        </div>
      </div>

      {(monitor.error || monitor.status?.error) && (
        <div className="mx-4 mb-3 rounded-md border border-red-900 bg-red-950/50 px-3 py-2 text-xs text-red-300">
          {monitor.error || monitor.status.error}
        </div>
      )}
      <div className="px-4 pb-3 text-[11px] text-slate-500">
        Last heartbeat: {formatDate(monitor.status?.last_heartbeat)}
        {monitor.status?.message && ` · ${monitor.status.message}`}
      </div>
    </section>
  )
}

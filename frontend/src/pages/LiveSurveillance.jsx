import React, { useState } from 'react'
import PageHeader from '../components/layout/PageHeader'
import CameraMonitor from '../components/surveillance/CameraMonitor'
import LiveVideoPanel from '../components/surveillance/LiveVideoPanel'
import TrackingSummary from '../components/surveillance/TrackingSummary'
import DetectionFeed from '../components/surveillance/DetectionFeed'
import { useSurveillance } from '../features/surveillance/useSurveillance'

export default function LiveSurveillance() {
  const [mode, setMode] = useState('image')
  const surveillance = useSurveillance()

  const handleFile = (file) => {
    if (mode === 'image') surveillance.runImageDetection(file)
    else surveillance.runVideoDetection(file)
  }

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <PageHeader title="Live surveillance" subtitle="Monitor a connected camera or run detection on uploaded media" />
      <CameraMonitor />
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.8fr)] gap-4">
        <LiveVideoPanel
          onFileSelected={handleFile}
          loading={surveillance.loading}
          error={surveillance.error}
          result={surveillance.result}
          mode={mode}
          onModeChange={(nextMode) => { setMode(nextMode); surveillance.reset() }}
        />
        <section className="panel min-h-64">
          <div className="panel-header"><h2 className="panel-title">Detection results</h2></div>
          <div className="p-4 space-y-5">
            {surveillance.result?.detections?.length ? (
              <TrackingSummary detections={surveillance.result.detections} />
            ) : surveillance.result?.events?.length ? (
              <TrackingSummary detections={surveillance.result.events.map((event) => ({
                class_name: event.class_name,
                confidence: event.confidence,
                bbox_xyxy: event.bbox,
                track_id: event.track_id,
              }))} />
            ) : (
              <p className="text-xs text-slate-500">Detection details appear here after an upload is processed.</p>
            )}
            <div className="border-t border-forest-800 pt-3">
              <p className="text-xs font-medium text-slate-400 mb-2">Recently logged detections</p>
              <DetectionFeed events={surveillance.result?.events ?? []} maxRows={8} />
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

import React, { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { fetchIncident, fetchIncidentImages } from '../../services/forestApi'
import { apiUrl } from '../../services/apiClient'
import { formatConfidence } from '../../utils/formatConfidence'
import { formatDate } from '../../utils/formatDate'
import { ClassBadge, PriorityBadge, ReviewBadge } from '../common/StatusBadge'
import ErrorState from '../common/ErrorState'
import LoadingState from '../common/LoadingState'

export default function EventDetailsDialog({ eventId, onClose }) {
  const [event, setEvent] = useState(null)
  const [images, setImages] = useState([])
  const [failedImages, setFailedImages] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!eventId) return undefined
    let active = true
    setLoading(true)
    setError(null)
    setFailedImages({})
    Promise.all([fetchIncident(eventId), fetchIncidentImages(eventId)])
      .then(([detail, imageList]) => {
        if (!active) return
        setEvent(detail)
        setImages(imageList)
      })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [eventId])

  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  if (!eventId) return null
  const imageBySequence = new Map(images.map((image) => [image.sequence, image]))
  const hasReliableDuration = Number.isFinite(event?.intrusion_duration_seconds)
    && event?.first_detection_time && event?.last_detection_time

  return (
    <div className="fixed inset-0 z-50 bg-black/70 p-3 sm:p-6 flex items-center justify-center" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <section role="dialog" aria-modal="true" aria-labelledby="event-dialog-title" className="panel w-full max-w-5xl max-h-[92vh] overflow-y-auto">
        <header className="sticky top-0 z-10 flex items-center justify-between gap-4 px-5 py-4 bg-surface-900 border-b border-forest-800">
          <div className="min-w-0">
            <h2 id="event-dialog-title" className="text-sm font-semibold text-slate-100">Event details</h2>
            <p className="text-xs text-slate-500 font-mono truncate mt-1">{eventId}</p>
          </div>
          <button className="btn-ghost p-2" onClick={onClose} aria-label="Close event details"><X className="w-4 h-4" /></button>
        </header>

        {loading ? <LoadingState message="Loading event and evidence…" rows={4} /> : error ? (
          <ErrorState message={error} />
        ) : event && (
          <div className="p-5 space-y-6">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div><p className="text-[11px] text-slate-500 mb-1">Detection</p><ClassBadge className={event.class_name} /></div>
              <div><p className="text-[11px] text-slate-500 mb-1">Confidence</p><p className="text-sm text-slate-200">{formatConfidence(event.confidence)}</p></div>
              <div><p className="text-[11px] text-slate-500 mb-1">Priority</p><PriorityBadge priority={event.alert_priority} /></div>
              <div><p className="text-[11px] text-slate-500 mb-1">Review status</p><ReviewBadge status={event.review_status} /></div>
              <div><p className="text-[11px] text-slate-500 mb-1">Timestamp</p><p className="text-xs text-slate-200">{formatDate(event.server_ts)}</p></div>
              <div><p className="text-[11px] text-slate-500 mb-1">Pole / Camera</p><p className="text-xs text-slate-200">{event.pole_id || '—'} / {event.camera_id || '—'}</p></div>
              <div><p className="text-[11px] text-slate-500 mb-1">Evidence images</p><p className="text-xs text-slate-200">{event.image_count ?? images.length} / 6</p></div>
              <div><p className="text-[11px] text-slate-500 mb-1">Location</p><p className="text-xs text-slate-200">{event.pole_location || 'Not configured'}</p></div>
            </div>

            {hasReliableDuration && (
              <div className="panel p-4">
                <h3 className="text-xs font-semibold text-slate-200 mb-2">Intrusion tracking</h3>
                <p className="text-xs text-slate-400">First: {formatDate(event.first_detection_time)} · Last: {formatDate(event.last_detection_time)} · Estimated duration: {Math.round(event.intrusion_duration_seconds)} seconds</p>
              </div>
            )}

            <div>
              <div className="flex items-baseline justify-between gap-3 mb-3">
                <h3 className="text-xs font-semibold text-slate-200">Burst evidence</h3>
                <span className="text-[11px] text-slate-500">Six JPEG frames stored for this event</span>
              </div>
              {images.length === 0 && <p className="text-xs text-amber-300 mb-3">No image metadata was returned for this event.</p>}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {Array.from({ length: 6 }, (_, index) => {
                  const sequence = index + 1
                  const image = imageBySequence.get(sequence)
                  const failed = !image || failedImages[sequence]
                  return (
                    <figure key={sequence} className="rounded-md overflow-hidden border border-forest-800 bg-surface-900">
                      {failed ? (
                        <div className="aspect-video flex items-center justify-center text-xs text-slate-500">
                          {image ? 'Image could not be loaded' : 'Image metadata unavailable'}
                        </div>
                      ) : (
                        <img
                          src={apiUrl(image.url)}
                          alt={`Event evidence frame ${sequence}`}
                          className="w-full aspect-video object-contain bg-black"
                          onError={() => setFailedImages((current) => ({ ...current, [sequence]: true }))}
                        />
                      )}
                      <figcaption className="px-3 py-2 flex justify-between gap-2 text-[11px]">
                        <span className="text-slate-300">Frame {String(sequence).padStart(2, '0')}</span>
                        <span className="text-slate-500 text-right">{formatDate(image?.capture_timestamp)}</span>
                      </figcaption>
                    </figure>
                  )
                })}
              </div>
            </div>
            {event.alert_label && <div className="rounded-md border border-amber-900 bg-amber-950/40 px-3 py-2 text-xs text-amber-200">{event.alert_label}</div>}
          </div>
        )}
      </section>
    </div>
  )
}

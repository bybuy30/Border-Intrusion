import React from 'react'
import { classDotClass, classTextClass } from '../../utils/severity'
import { formatConfidence } from '../../utils/formatConfidence'

export default function TrackingSummary({ detections = [] }) {
  if (!detections.length) return null
  return (
    <div className="space-y-1">
      <p className="text-xs text-slate-500 mb-2">Detection breakdown</p>
      {detections.map((det, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full shrink-0 ${classDotClass(det.class_name)}`} />
          <span className={`font-medium ${classTextClass(det.class_name)}`}>{det.class_name}</span>
          <span className="text-slate-400 tabular-nums">{formatConfidence(det.confidence)}</span>
          {det.track_id != null && (
            <span className="text-slate-600 font-mono">#{det.track_id}</span>
          )}
          <span className="text-slate-600 truncate text-[10px]">
            [{det.bbox_xyxy?.map((v) => Math.round(v)).join(', ')}]
          </span>
        </div>
      ))}
      <p className="text-[10px] text-slate-600 pt-1">
        Track IDs are temporary session identifiers and do not identify individuals.
      </p>
    </div>
  )
}

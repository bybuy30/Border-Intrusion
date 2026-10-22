import React from 'react'
import { formatConfidence } from '../../utils/formatConfidence'

const CLASS_STROKE = { animal: '#68a356', person: '#60a5fa', firearm: '#f87171' }
const DEFAULT_STROKE = '#94a3b8'

/**
 * Renders SVG bounding-box overlays on top of an image.
 *
 * @param {object}   props
 * @param {Array}    props.detections  - Array of detection objects from the API
 * @param {number}   props.imgWidth    - Natural width of the displayed image
 * @param {number}   props.imgHeight   - Natural height of the displayed image
 * @param {number}   props.displayW    - Rendered display width (for scaling)
 * @param {number}   props.displayH    - Rendered display height (for scaling)
 */
export default function DetectionOverlay({ detections = [], imgWidth = 640, imgHeight = 640, displayW, displayH }) {
  if (!detections.length) return null

  const scaleX = displayW ? displayW / imgWidth : 1
  const scaleY = displayH ? displayH / imgHeight : 1

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={displayW ?? imgWidth}
      height={displayH ?? imgHeight}
      viewBox={`0 0 ${displayW ?? imgWidth} ${displayH ?? imgHeight}`}
    >
      {detections.map((det, i) => {
        const [x1, y1, x2, y2] = det.bbox_xyxy ?? [0, 0, 0, 0]
        const sx1 = x1 * scaleX
        const sy1 = y1 * scaleY
        const sw  = (x2 - x1) * scaleX
        const sh  = (y2 - y1) * scaleY
        const stroke = CLASS_STROKE[det.class_name] ?? DEFAULT_STROKE
        const label  = `${det.class_name} ${formatConfidence(det.confidence)}`

        return (
          <g key={i}>
            <rect
              x={sx1} y={sy1} width={sw} height={sh}
              fill="none" stroke={stroke} strokeWidth={1.5}
              rx={2}
            />
            <rect
              x={sx1} y={sy1 - 16} width={label.length * 6.2 + 8} height={16}
              fill={stroke} fillOpacity={0.85} rx={2}
            />
            <text
              x={sx1 + 4} y={sy1 - 4}
              fontSize={10} fill="#fff" fontFamily="monospace"
            >
              {label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

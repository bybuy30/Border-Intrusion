import React, { useState, useRef, useCallback } from 'react'
import { Upload, ImageIcon, Film, AlertTriangle } from 'lucide-react'
import DetectionOverlay from './DetectionOverlay'
import LoadingState from '../common/LoadingState'
import ErrorState from '../common/ErrorState'

const ACCEPT_IMAGE = 'image/jpeg,image/png,image/bmp,image/webp'
const ACCEPT_VIDEO = 'video/mp4,video/avi,video/quicktime,video/x-matroska'

export default function LiveVideoPanel({ onFileSelected, loading, error, result, mode, onModeChange }) {
  const [dragOver, setDragOver]     = useState(false)
  const [preview, setPreview]       = useState(null)  // object-URL for image preview
  const [imgNaturalSize, setNaturalSize] = useState({ w: 640, h: 640 })
  const [displaySize, setDisplaySize]   = useState({ w: 0, h: 0 })
  const imgRef   = useRef(null)
  const inputRef = useRef(null)

  const accept = mode === 'image' ? ACCEPT_IMAGE : ACCEPT_VIDEO

  const handleFile = useCallback((file) => {
    if (!file) return
    if (mode === 'image' && file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file)
      setPreview(url)
    } else {
      setPreview(null)
    }
    onFileSelected(file)
  }, [mode, onFileSelected])

  const onInputChange = (e) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''   // allow re-selecting same file
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  const onImgLoad = () => {
    if (imgRef.current) {
      setNaturalSize({ w: imgRef.current.naturalWidth,  h: imgRef.current.naturalHeight })
      setDisplaySize({ w: imgRef.current.offsetWidth,   h: imgRef.current.offsetHeight })
    }
  }

  const detections = result?.detections ?? []
  const hasFirearm = detections.some((d) => d.class_name === 'firearm')

  return (
    <div className="panel flex flex-col h-full">
      {/* Mode toggle */}
      <div className="panel-header">
        <span className="panel-title">Detection Input</span>
        <div className="flex rounded-md overflow-hidden border border-forest-700">
          {['image', 'video'].map((m) => (
            <button
              key={m}
              onClick={() => { onModeChange(m); setPreview(null) }}
              className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium transition-colors
                ${mode === m ? 'bg-forest-700 text-forest-200' : 'text-slate-400 hover:bg-surface-600'}`}
            >
              {m === 'image' ? <ImageIcon className="w-3 h-3" /> : <Film className="w-3 h-3" />}
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <div
        className={`flex-1 flex flex-col items-center justify-center p-4 cursor-pointer
          border-2 border-dashed rounded-b-panel m-2 transition-colors
          ${dragOver ? 'border-forest-500 bg-forest-900/30' : 'border-forest-800 hover:border-forest-600'}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={onInputChange} />

        {loading ? (
          <LoadingState message="Running detection…" rows={3} />
        ) : error ? (
          <ErrorState message={error} />
        ) : preview ? (
          <div className="relative w-full flex justify-center">
            <img
              ref={imgRef}
              src={preview}
              alt="Preview"
              className="max-h-80 object-contain rounded"
              onLoad={onImgLoad}
            />
            {result && (
              <DetectionOverlay
                detections={detections}
                imgWidth={imgNaturalSize.w}
                imgHeight={imgNaturalSize.h}
                displayW={displaySize.w}
                displayH={displaySize.h}
              />
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center pointer-events-none">
            <Upload className="w-8 h-8 text-slate-600" />
            <p className="text-sm text-slate-400">
              Drop {mode === 'image' ? 'an image' : 'a video'} here, or click to browse
            </p>
            <p className="text-xs text-slate-600">
              {mode === 'image' ? 'JPG, PNG, BMP, WEBP' : 'MP4, AVI, MOV, MKV'}
            </p>
            <p className="text-xs text-slate-600 italic mt-1">
              ⚠ Upload-only — no live camera feed connected
            </p>
          </div>
        )}
      </div>

      {/* Firearm warning */}
      {hasFirearm && (
        <div className="mx-2 mb-2 flex items-start gap-2 px-3 py-2 bg-red-950 border border-red-800 rounded-md">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">
            <span className="font-semibold">Potential weapon detected — review required.</span>{' '}
            This is an automated observation only and does not constitute confirmation of illegal activity.
          </p>
        </div>
      )}

      {/* Result summary */}
      {result && !loading && (
        <div className="px-4 pb-3 pt-1 border-t border-forest-800">
          <p className="text-xs text-slate-400">
            <span className="text-slate-200 font-medium">{result.detections_count ?? result.total_detections ?? 0}</span> detection(s)
            {result.latency_ms != null && (
              <span className="ml-2 text-slate-600">· {result.latency_ms} ms</span>
            )}
            {result.frames_sampled != null && (
              <span className="ml-2 text-slate-600">· {result.frames_sampled} frames sampled</span>
            )}
          </p>
        </div>
      )}
    </div>
  )
}

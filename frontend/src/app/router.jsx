import React, { lazy, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'

const CommandCenter = lazy(() => import('../pages/CommandCenter'))
const LiveSurveillance = lazy(() => import('../pages/LiveSurveillance'))
const IncidentLog = lazy(() => import('../pages/IncidentLog'))
const Analytics = lazy(() => import('../pages/Analytics'))
const DeviceManagement = lazy(() => import('../pages/DeviceManagement'))
const ModelPerformance = lazy(() => import('../pages/ModelPerformance'))
const NotFound = lazy(() => import('../pages/NotFound'))

function page(Page) {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500">Loading dashboard page…</div>}>
      <Page />
    </Suspense>
  )
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true,              element: page(CommandCenter) },
      { path: 'surveillance',     element: page(LiveSurveillance) },
      { path: 'incidents',        element: page(IncidentLog) },
      { path: 'incidents/:id',    element: page(IncidentLog) },
      { path: 'analytics',        element: page(Analytics) },
      { path: 'devices',          element: page(DeviceManagement) },
      { path: 'model',            element: page(ModelPerformance) },
      { path: '*',                element: page(NotFound) },
    ],
  },
])

import React from 'react'
import { createBrowserRouter } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import CommandCenter from '../pages/CommandCenter'
import LiveSurveillance from '../pages/LiveSurveillance'
import IncidentLog from '../pages/IncidentLog'
import PerimeterMapPage from '../pages/PerimeterMapPage'
import Analytics from '../pages/Analytics'
import DeviceManagement from '../pages/DeviceManagement'
import ModelPerformance from '../pages/ModelPerformance'
import NotFound from '../pages/NotFound'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true,              element: <CommandCenter /> },
      { path: 'surveillance',     element: <LiveSurveillance /> },
      { path: 'incidents',        element: <IncidentLog /> },
      { path: 'incidents/:id',    element: <IncidentLog /> },
      { path: 'perimeter',        element: <PerimeterMapPage /> },
      { path: 'analytics',        element: <Analytics /> },
      { path: 'devices',          element: <DeviceManagement /> },
      { path: 'model',            element: <ModelPerformance /> },
      { path: '*',                element: <NotFound /> },
    ],
  },
])

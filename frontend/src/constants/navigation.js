// Navigation items for the sidebar
// icon: string name matching a Lucide icon (resolved in Sidebar.jsx)

export const NAV_ITEMS = [
  {
    label: 'Command Center',
    path: '/',
    icon: 'LayoutDashboard',
    exact: true,
  },
  {
    label: 'Live Surveillance',
    path: '/surveillance',
    icon: 'Video',
  },
  {
    label: 'Incident Log',
    path: '/incidents',
    icon: 'AlertTriangle',
  },
  {
    label: 'Perimeter Map',
    path: '/perimeter',
    icon: 'Map',
  },
  {
    label: 'Analytics',
    path: '/analytics',
    icon: 'BarChart2',
  },
  {
    label: 'Devices',
    path: '/devices',
    icon: 'Cpu',
  },
  {
    label: 'Model Performance',
    path: '/model',
    icon: 'Activity',
  },
]

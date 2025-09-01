import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ToastProvider } from './context/ToastContext'
import RootLayout from './RootLayout'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import ProjectPage from './pages/ProjectPage'
import ReviewTakeoffPage from './pages/ReviewTakeoffPage'
import ReviewEstimatePage from './pages/ReviewEstimatePage'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="projects/:pid" element={<ProjectPage />} />
            <Route path="projects/:pid/review/takeoff" element={<ReviewTakeoffPage />} />
            <Route path="projects/:pid/review/estimate" element={<ReviewEstimatePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  </React.StrictMode>
)

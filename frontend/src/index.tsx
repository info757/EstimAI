import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ToastProvider } from './context/ToastContext'
import RootLayout from './RootLayout'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import ProjectPage from './pages/ProjectPage'
import ReviewPage from './pages/ReviewPage'
import ReviewTakeoffPage from './pages/ReviewTakeoffPage'
import ReviewEstimatePage from './pages/ReviewEstimatePage'
import LoginPage from './pages/LoginPage'
import VectorTakeoffPage from './pages/vector-takeoff'
import PrivateRoute from './components/PrivateRoute'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="upload" element={
              <PrivateRoute>
                <UploadPage />
              </PrivateRoute>
            } />
            <Route path="login" element={<LoginPage />} />
            <Route path="projects/:pid" element={
              <PrivateRoute>
                <ProjectPage />
              </PrivateRoute>
            } />
            <Route path="projects/:pid/review" element={
              <PrivateRoute>
                <ReviewPage />
              </PrivateRoute>
            } />
            <Route path="projects/:pid/review/takeoff" element={
              <PrivateRoute>
                <ReviewTakeoffPage />
              </PrivateRoute>
            } />
            <Route path="projects/:pid/review/estimate" element={
              <PrivateRoute>
                <ReviewEstimatePage />
              </PrivateRoute>
            } />
            <Route path="vector-takeoff" element={<VectorTakeoffPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  </React.StrictMode>
)

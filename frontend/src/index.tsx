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
import LoginPage from './pages/LoginPage'
import PrivateRoute from './components/PrivateRoute'
import DemoAwareRoute from './components/DemoAwareRoute'

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
              <DemoAwareRoute>
                <ProjectPage />
              </DemoAwareRoute>
            } />
            <Route path="projects/:pid/review/takeoff" element={
              <DemoAwareRoute>
                <ReviewTakeoffPage />
              </DemoAwareRoute>
            } />
            <Route path="projects/:pid/review/estimate" element={
              <DemoAwareRoute>
                <ReviewEstimatePage />
              </DemoAwareRoute>
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  </React.StrictMode>
)

import { Outlet, Link } from 'react-router-dom'

export default function RootLayout() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="flex items-center justify-between px-6 py-4 shadow bg-white">
        <Link to="/" className="font-semibold">EstimAI</Link>
        <nav className="space-x-4">
          <Link to="/upload" className="underline">Upload</Link>
        </nav>
      </header>
      <main className="max-w-5xl mx-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}

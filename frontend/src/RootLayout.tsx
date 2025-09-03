import { Outlet, Link, useNavigate } from 'react-router-dom'
import { isAuthenticated, getUser, logout } from './state/auth'

export default function RootLayout() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  const user = getUser();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="flex items-center justify-between px-6 py-4 shadow bg-white">
        <Link to="/" className="font-semibold">EstimAI</Link>
        <nav className="flex items-center space-x-4">
          <Link to="/upload" className="underline">Upload</Link>
          {authenticated ? (
            <>
              <span className="text-sm text-gray-600">
                Welcome, {user?.name || user?.email}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm text-red-600 hover:text-red-800 underline"
              >
                Logout
              </button>
            </>
          ) : (
            <Link to="/login" className="text-blue-600 hover:text-blue-800 underline">
              Login
            </Link>
          )}
        </nav>
      </header>
      <main className="max-w-5xl mx-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}

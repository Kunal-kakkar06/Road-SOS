import { Navigate, Outlet } from 'react-router-dom';

export default function ProtectedRoute({ allowedRoles }) {
  const token = localStorage.getItem('accessToken');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles) {
    try {
      const cachedUser = localStorage.getItem('user');
      const user = cachedUser ? JSON.parse(cachedUser) : null;
      const role = user ? user.role : 'USER';
      if (!allowedRoles.includes(role)) {
        return <Navigate to="/403" replace />;
      }
    } catch (_) {
      return <Navigate to="/403" replace />;
    }
  }

  return <Outlet />;
}

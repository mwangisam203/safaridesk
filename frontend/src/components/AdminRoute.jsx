import { LoaderCircle } from "lucide-react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="grid min-h-[70vh] place-items-center">
        <LoaderCircle className="animate-spin text-green-600" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  if (!user.is_admin || !user.is_verified || !user.is_active) {
    return <Navigate to="/account" replace />;
  }

  return children;
}

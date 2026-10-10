import { Navigate, Outlet } from "react-router";
import { useAuth } from "../contexts/AuthContext";
import { components } from "../api/schema";
import { Loader2 } from "lucide-react";

type Role = components["schemas"]["Role"];

interface ProtectedRouteProps {
  allowedRoles?: Role[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Standard unprivileged users should bounce back to home
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Component for protecting routes that require authentication in the Gmail Cleaner application.

// Import necessary modules and components
import { Navigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

// Define the ProtectedRoute component that checks for authentication before rendering its children
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

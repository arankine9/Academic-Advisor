import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { currentUser, loading } = useAuth();

  // Show loading state if still checking authentication
  if (loading) {
    return <div className="container">Loading...</div>;
  }

  // Redirect to login if not authenticated
  if (!currentUser) {
    return <Navigate to="/" />;
  }

  // If authenticated, render the protected component
  return children;
};

export default ProtectedRoute;
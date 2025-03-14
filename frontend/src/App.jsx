import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import ProtectedRoute from './components/ProtectedRoute';
import Notification from './components/Notification';
import ClassManagement from './components/ClassManagement';
import AdvisingChat from './components/AdvisingChat';

// Import pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

// Import CSS
import './index.css';

const App = () => {
  return (
    <Router>
      <NotificationProvider>
        <AuthProvider>
          <Notification />
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Login />} />
            
            {/* Protected routes */}
            <Route 
              path="/dashboard" 
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/classes" 
              element={
                <ProtectedRoute>
                  <ClassManagement />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/advising" 
              element={
                <ProtectedRoute>
                  <AdvisingChat />
                </ProtectedRoute>
              } 
            />
            
            {/* Redirect to dashboard if path is unknown */}
            <Route path="*" element={<Navigate to="/dashboard" />} />
          </Routes>
        </AuthProvider>
      </NotificationProvider>
    </Router>
  );
};

export default App;
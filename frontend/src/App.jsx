import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import ProtectedRoute from './components/ProtectedRoute';
import Notification from './components/Notification';
import AdvisingChat from './components/AdvisingChat';
import AppBackground from './components/background';

// Import pages
import Login from './pages/Login';

// Import CSS
import './index.css';

const App = () => {
  return (
    <Router>
      <NotificationProvider>
        <AuthProvider>
          <AppBackground>
            <Notification />
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<Login />} />
              
              {/* Protected routes */}
              <Route 
                path="/advising" 
                element={
                  <ProtectedRoute>
                    <AdvisingChat />
                  </ProtectedRoute>
                } 
              />
              
              {/* Redirect to advising if path is unknown */}
              <Route path="*" element={<Navigate to="/advising" />} />
            </Routes>
          </AppBackground>
        </AuthProvider>
      </NotificationProvider>
    </Router>
  );
};

export default App;
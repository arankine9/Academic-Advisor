import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser, registerUser, getCurrentUser } from '../services/authService';

// Create a context for authentication
const AuthContext = createContext();

// Hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};

// Provider component
export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Check if user is logged in on initial load
  useEffect(() => {
    const checkLoggedIn = async () => {
      try {
        const token = localStorage.getItem('token');
        if (token) {
          const userData = await getCurrentUser();
          setCurrentUser(userData);
        }
      } catch (error) {
        console.error('Authentication check failed:', error);
        localStorage.removeItem('token');
      } finally {
        setLoading(false);
      }
    };

    checkLoggedIn();
  }, []);

  // Login function
  const login = async (username, password) => {
    try {
      setError(null);
      const data = await loginUser(username, password);
      
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        const userData = await getCurrentUser();
        setCurrentUser(userData);
        return true;
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Login failed');
      return false;
    }
  };

  // Register function
  const register = async (username, email, password, major) => {
    try {
      setError(null);
      const data = await registerUser(username, email, password, major);
      
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        const userData = await getCurrentUser();
        setCurrentUser(userData);
        return true;
      }
      return true; // Registration successful but no auto-login
    } catch (error) {
      setError(error.response?.data?.detail || 'Registration failed');
      return false;
    }
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('token');
    setCurrentUser(null);
    navigate('/');
  };

  // Value object to be provided by context
  const value = {
    currentUser,
    login,
    register,
    logout,
    error,
    setError,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
import React, { createContext, useState, useContext } from 'react';

// Create notification context
const NotificationContext = createContext();

// Hook to use the notification context
export const useNotification = () => {
  return useContext(NotificationContext);
};

// Provider component
export const NotificationProvider = ({ children }) => {
  const [notification, setNotification] = useState({
    message: '',
    isVisible: false,
    isSuccess: true
  });

  // Show notification
  const showNotification = (message, isSuccess = true) => {
    setNotification({
      message,
      isVisible: true,
      isSuccess
    });

    // Auto-hide after 3 seconds
    setTimeout(() => {
      setNotification(prev => ({
        ...prev,
        isVisible: false
      }));
    }, 3000);
  };

  // Value object to be provided by context
  const value = {
    notification,
    showNotification
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export default NotificationContext;
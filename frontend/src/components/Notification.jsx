import React from 'react';
import { useNotification } from '../context/NotificationContext';

const Notification = () => {
  const { notification } = useNotification();
  const { message, isVisible, isSuccess } = notification;

  if (!isVisible) {
    return null;
  }

  const backgroundColor = isSuccess ? 'rgba(39, 174, 96, 0.9)' : 'rgba(231, 76, 60, 0.9)';

  return (
    <div 
      className={`notification ${isVisible ? 'show' : ''}`}
      style={{ backgroundColor }}
    >
      {message}
    </div>
  );
};

export default Notification;
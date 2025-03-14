import React from 'react';
import backgroundImage from '../assets/images/old_main.jpg';

const AppBackground = ({ children }) => {
  // Set background style on the component
  const backgroundStyle = {
    backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), url(${backgroundImage})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat', 
    backgroundAttachment: 'fixed',
    minHeight: '100vh',
    position: 'relative',
    overflow: 'hidden',
    color: 'white',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
  };

  return (
    <div style={backgroundStyle}>
      {children}
    </div>
  );
};

export default AppBackground;
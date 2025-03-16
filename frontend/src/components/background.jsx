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

  // Add backdrop filter to create the blur effect
  const containerStyle = {
    width: '100%',
    minHeight: '100vh',
    backdropFilter: 'blur(10px)',
    display: 'flex',
    flexDirection: 'column',
  };

  return (
    <div style={backgroundStyle}>
      <div style={containerStyle}>
        {children}
      </div>
    </div>
  );
};

export default AppBackground;
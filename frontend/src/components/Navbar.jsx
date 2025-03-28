import React from 'react';
import { useAuth } from '../context/AuthContext';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSignOutAlt } from '@fortawesome/free-solid-svg-icons';

const Navbar = () => {
  const { currentUser, logout } = useAuth();

  // If no user, don't render navbar
  if (!currentUser) {
    return null;
  }

  return (
    <div className="navbar">
      <div className="navbar-left">
        {/* No navigation links since we only have one main page now */}
      </div>
      <div className="navbar-right">
        <span className="navbar-username">
          {currentUser.username}
        </span>
        <button id="logout-btn" onClick={logout}>
          <FontAwesomeIcon icon={faSignOutAlt} style={{ marginRight: '8px' }} />
          Logout
        </button>
      </div>
    </div>
  );
};

export default Navbar;
import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTimes } from '@fortawesome/free-solid-svg-icons';

const MajorItem = ({ major, onRemove }) => {
  const handleRemove = () => {
    onRemove(major.id);
  };

  return (
    <div className="major-item">
      <span className="major-name">{major.name}</span>
      <button 
        className="remove-button" 
        onClick={handleRemove}
        aria-label={`Remove ${major.name}`}
      >
        <FontAwesomeIcon icon={faTimes} />
      </button>
    </div>
  );
};

export default MajorItem; 
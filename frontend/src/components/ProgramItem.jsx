import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTimes } from '@fortawesome/free-solid-svg-icons';

const ProgramItem = ({ program, onRemove }) => {
  const handleRemove = () => {
    // Using program_name instead of id for removal
    onRemove(program.program_name);
  };

  return (
    <div className="program-item">
      <span className="program-name">{program.program_name}</span>
      <button 
        className="remove-button" 
        onClick={handleRemove}
        aria-label={`Remove ${program.program_name}`}
      >
        <FontAwesomeIcon icon
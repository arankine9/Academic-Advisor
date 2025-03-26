import React, { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPenToSquare, faTrash } from '@fortawesome/free-solid-svg-icons';

const CourseItem = ({ 
  course, 
  onRemove, 
  onStartEdit, 
  onSaveEdit, 
  onCancelEdit, 
  isEditing 
}) => {
  const [editData, setEditData] = useState({
    department: course.department || course.class_code.split(' ')[0],
    course_number: course.course_number || course.class_code.split(' ')[1],
    name: course.name || course.course_name,
    term: course.term || ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setEditData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSave = () => {
    onSaveEdit(course.id, editData);
  };

  // Parse course code if needed
  const parseCourseCode = () => {
    if (course.department && course.course_number) {
      return `${course.department} ${course.course_number}`;
    }
    return course.class_code;
  };

  // Display mode
  if (!isEditing) {
    return (
      <div className="course-item" style={{
        opacity: 0,
        transform: 'translateY(20px)',
        transition: 'opacity 0.3s ease, transform 0.3s ease',
        animation: 'none'
      }} ref={el => {
        if (el) {
          setTimeout(() => {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
          }, 50);
        }
      }}>
        <div className="course-info">
          <div className="course-code">{parseCourseCode()}</div>
          <div className="course-name">{course.name || course.course_name || 'No name provided'}</div>
          <div className="course-term">{course.term || 'No term specified'}</div>
        </div>
        <div className="course-actions">
          <button className="edit-btn" onClick={() => onStartEdit(course.id)}>
            <FontAwesomeIcon icon={faPenToSquare} />
          </button>
          <button className="remove-btn" onClick={() => onRemove(course.id)}>
            <FontAwesomeIcon icon={faTrash} />
          </button>
        </div>
      </div>
    );
  }

  // Edit mode
  return (
    <div className="course-item edit-mode">
      <div className="course-info">
        <div className="form-row">
          <div className="form-group" style={{ minWidth: '100px' }}>
            <input 
              type="text" 
              name="department"
              value={editData.department} 
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group" style={{ minWidth: '100px' }}>
            <input 
              type="text" 
              name="course_number"
              value={editData.course_number} 
              onChange={handleChange}
              required
            />
          </div>
        </div>
        <div className="form-group">
          <input 
            type="text" 
            name="name"
            value={editData.name || ''} 
            onChange={handleChange}
            placeholder="Course name"
          />
        </div>
        <div className="form-group">
          <select 
            name="term"
            value={editData.term || ''} 
            onChange={handleChange}
          >
            <option value="">-- Select Term --</option>
            <option value="Fall 2023">Fall 2023</option>
            <option value="Spring 2023">Spring 2023</option>
            <option value="Fall 2022">Fall 2022</option>
            <option value="Spring 2022">Spring 2022</option>
          </select>
        </div>
      </div>
      <div className="course-actions">
        <button className="edit-btn" onClick={handleSave}>Save</button>
        <button className="remove-btn" onClick={() => onCancelEdit(course.id)}>Cancel</button>
      </div>
    </div>
  );
};

export default CourseItem;
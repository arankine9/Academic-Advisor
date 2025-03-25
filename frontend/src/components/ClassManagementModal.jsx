import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faPlus, 
  faBuildingColumns, 
  faHashtag, 
  faCalendar, 
  faBook,
  faTimes,
  faGraduationCap,
  faChevronDown
} from '@fortawesome/free-solid-svg-icons';

import CourseItem from './CourseItem';
import MajorItem from './MajorItem';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { 
  getUserCourses, 
  addCourse, 
  removeCourse, 
  updateCourse 
} from '../services/courseService';
import {
  getAvailableMajors,
  getUserMajors,
  addMajor,
  removeMajor
} from '../services/majorService';

import './ClassManagementModal.css';

const ClassManagementModal = ({ isOpen, onClose }) => {
  const { currentUser } = useAuth();
  const { showNotification } = useNotification();
  
  const [courses, setCourses] = useState([]);
  const [majors, setMajors] = useState([]);
  const [availableMajors, setAvailableMajors] = useState([]);
  const [selectedMajor, setSelectedMajor] = useState('');
  const [isMajorsExpanded, setIsMajorsExpanded] = useState(false);
  const [formData, setFormData] = useState({
    department: '',
    courseNumber: '',
    courseName: '',
    term: ''
  });
  const [editingCourseId, setEditingCourseId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMajors, setLoadingMajors] = useState(true);

  // Load user courses on component mount and when modal opens
  useEffect(() => {
    if (isOpen) {
      loadUserCourses();
      loadUserMajors();
      loadAvailableMajors();
    }
  }, [isOpen]);

  // Function to load user courses
  const loadUserCourses = async () => {
    try {
      setLoading(true);
      const userCourses = await getUserCourses();
      setCourses(userCourses);
    } catch (error) {
      console.error('Error loading courses:', error);
      showNotification('Failed to load courses', false);
    } finally {
      setLoading(false);
    }
  };

  // Function to load user majors
  const loadUserMajors = async () => {
    try {
      setLoadingMajors(true);
      const userMajors = await getUserMajors();
      setMajors(userMajors);
    } catch (error) {
      console.error('Error loading majors:', error);
      showNotification('Failed to load majors', false);
    } finally {
      setLoadingMajors(false);
    }
  };

  // Function to load available majors
  const loadAvailableMajors = async () => {
    try {
      const majors = await getAvailableMajors();
      setAvailableMajors(majors);
    } catch (error) {
      console.error('Error loading available majors:', error);
      showNotification('Failed to load available majors', false);
    }
  };

  // Handle form input change
  const handleChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [id]: value
    }));
  };

  // Handle major selection change
  const handleMajorChange = (e) => {
    setSelectedMajor(e.target.value);
  };

  // Handle add course form submission
  const handleAddCourse = async (e) => {
    e.preventDefault();
    
    try {
      const { department, courseNumber, courseName, term } = formData;
      
      const newCourse = await addCourse(
        department.trim().toUpperCase(),
        courseNumber.trim(),
        courseName.trim(),
        term
      );
      
      // Add to local state
      setCourses(prev => [...prev, newCourse]);
      
      // Clear form
      setFormData({
        department: '',
        courseNumber: '',
        courseName: '',
        term: ''
      });
      
      showNotification('Course added successfully');
    } catch (error) {
      console.error('Error adding course:', error);
      showNotification('Failed to add course', false);
    }
  };

  // Handle add major
  const handleAddMajor = async () => {
    if (!selectedMajor) {
      showNotification('Please select a major', false);
      return;
    }

    // Check if major is already added
    if (majors.some(major => major.name === selectedMajor)) {
      showNotification('This major is already added', false);
      return;
    }
    
    try {
      const newMajor = await addMajor(selectedMajor);
      
      // Add to local state
      setMajors(prev => [...prev, newMajor]);
      
      // Clear selection
      setSelectedMajor('');
      
      showNotification('Major added successfully');
    } catch (error) {
      console.error('Error adding major:', error);
      showNotification('Failed to add major', false);
    }
  };

  // Handle remove major
  const handleRemoveMajor = async (majorId) => {
    if (!window.confirm('Are you sure you want to remove this major?')) {
      return;
    }
    
    try {
      await removeMajor(majorId);
      
      // Remove from local state
      setMajors(prev => prev.filter(major => major.id !== majorId));
      
      showNotification('Major removed successfully');
    } catch (error) {
      console.error('Error removing major:', error);
      showNotification('Failed to remove major', false);
    }
  };

  // Start editing a course
  const startEdit = (courseId) => {
    setEditingCourseId(courseId);
  };

  // Cancel editing
  const cancelEdit = () => {
    setEditingCourseId(null);
  };

  // Save edited course
  const saveEdit = async (courseId, courseData) => {
    try {
      const { department, course_number, name, term } = courseData;
      
      const updatedCourse = await updateCourse(courseId, {
        department: department.trim().toUpperCase(),
        course_number: course_number.trim(),
        name: name.trim(),
        term
      });
      
      // Update in local state
      setCourses(prev => prev.map(course => 
        course.id === courseId ? updatedCourse : course
      ));
      
      // Exit edit mode
      setEditingCourseId(null);
      
      showNotification('Course updated successfully');
    } catch (error) {
      console.error('Error updating course:', error);
      showNotification('Failed to update course', false);
    }
  };

  // Remove course
  const handleRemoveCourse = async (courseId) => {
    if (!window.confirm('Are you sure you want to remove this course?')) {
      return;
    }
    
    try {
      await removeCourse(courseId);
      
      // Remove from local state
      setCourses(prev => prev.filter(course => course.id !== courseId));
      
      showNotification('Course removed successfully');
    } catch (error) {
      console.error('Error removing course:', error);
      showNotification('Failed to remove course', false);
    }
  };

  // If modal is not open, don't render anything
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Class Management</h2>
          <button className="close-button" onClick={onClose}>
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>
        
        <div className="modal-body">
          <div id="major-management" className="major-management">
            <div 
              className="major-header"
              onClick={() => setIsMajorsExpanded(!isMajorsExpanded)}
            >
              <h3>
                <FontAwesomeIcon icon={faGraduationCap} style={{ marginRight: '10px' }} />
                Majors
              </h3>
              <FontAwesomeIcon 
                icon={faChevronDown} 
                className={`chevron-icon ${isMajorsExpanded ? 'expanded' : ''}`}
              />
            </div>
            
            <div className={`major-content ${isMajorsExpanded ? 'expanded' : ''}`}>
              <div className="major-select-container">
                <label htmlFor="major-select">Select a major to add:</label>
                <select 
                  id="major-select" 
                  className="major-select"
                  value={selectedMajor}
                  onChange={handleMajorChange}
                >
                  <option value="">Select a Major</option>
                  {availableMajors.map((major, index) => (
                    <option key={index} value={major}>{major}</option>
                  ))}
                </select>
                
                <button 
                  className="add-major-btn"
                  onClick={handleAddMajor}
                  disabled={!selectedMajor}
                >
                  <FontAwesomeIcon icon={faPlus} />
                  Add Major
                </button>
              </div>
              
              <h4>Your Majors:</h4>
              <div className="major-list">
                {loadingMajors ? (
                  <div className="no-majors-message">Loading majors...</div>
                ) : majors.length === 0 ? (
                  <div className="no-majors-message">You haven't added any majors yet.</div>
                ) : (
                  majors.map(major => (
                    <MajorItem 
                      key={major.id}
                      major={major}
                      onRemove={handleRemoveMajor}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
          
          <div id="course-management">
            <div className="dashboard-summary">
              <h3>
                <FontAwesomeIcon icon={faPlus} style={{ marginRight: '10px' }} />
                Add a Completed Course
              </h3>
              
              <form id="add-course-form" onSubmit={handleAddCourse}>
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="department">Department</label>
                    <div className="input-wrapper">
                      <FontAwesomeIcon icon={faBuildingColumns} className="classes-icon" />
                      <input 
                        type="text" 
                        id="department" 
                        placeholder="e.g., CS, MATH, PHYS"
                        value={formData.department}
                        onChange={handleChange}
                        required
                      />
                    </div>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="courseNumber">Course Number</label>
                    <div className="input-wrapper">
                      <FontAwesomeIcon icon={faHashtag} className="classes-icon" />
                      <input 
                        type="text" 
                        id="courseNumber" 
                        placeholder="e.g., 101, 210, 350"
                        value={formData.courseNumber}
                        onChange={handleChange}
                        required
                      />
                    </div>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="term">Term Taken</label>
                    <div className="input-wrapper">
                      <FontAwesomeIcon icon={faCalendar} className="classes-icon" />
                      <select 
                        id="term"
                        value={formData.term}
                        onChange={handleChange}
                      >
                        <option value="">Select Term</option>
                        <option value="Fall 2023">Fall 2023</option>
                        <option value="Spring 2023">Spring 2023</option>
                        <option value="Fall 2022">Fall 2022</option>
                        <option value="Spring 2022">Spring 2022</option>
                      </select>
                    </div>
                  </div>
                </div>
                
                <div className="form-group">
                  <label htmlFor="courseName">Course Name</label>
                  <div className="input-wrapper">
                    <FontAwesomeIcon icon={faBook} className="classes-icon" />
                    <input 
                      type="text" 
                      id="courseName" 
                      placeholder="e.g., Introduction to Computer Science"
                      value={formData.courseName}
                      onChange={handleChange}
                    />
                  </div>
                </div>
                
                <button type="submit" id="addCourseBtn">
                  <FontAwesomeIcon icon={faPlus} style={{ marginRight: '8px' }} />
                  Add Course
                </button>
              </form>
            </div>
            
            <h3>
              <FontAwesomeIcon icon={faBook} style={{ marginRight: '10px' }} />
              Your Completed Courses
            </h3>
            <div id="courseList">
              {loading ? (
                <div className="no-courses-message">Loading courses...</div>
              ) : courses.length === 0 ? (
                <div className="no-courses-message">You haven't added any courses yet.</div>
              ) : (
                courses.map(course => (
                  <CourseItem 
                    key={course.id}
                    course={course}
                    onRemove={handleRemoveCourse}
                    onStartEdit={startEdit}
                    onSaveEdit={saveEdit}
                    onCancelEdit={cancelEdit}
                    isEditing={course.id === editingCourseId}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClassManagementModal; 
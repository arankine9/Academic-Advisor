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
import ProgramItem from './ProgramItem';  // Updated import
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { 
  getUserCourses, 
  addCourse, 
  removeCourse, 
  updateCourse 
} from '../services/courseService';
import {
  getAvailablePrograms,
  getUserPrograms,
  assignProgramFromTemplate,
  addCustomProgram,
  removeProgram
} from '../services/programService';  // Updated import

import './ClassManagementModal.css';

const ClassManagementModal = ({ isOpen, onClose }) => {
  const { currentUser } = useAuth();
  const { showNotification } = useNotification();
  
  const [courses, setCourses] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [availablePrograms, setAvailablePrograms] = useState([]);
  const [selectedProgramId, setSelectedProgramId] = useState('');
  const [isProgramsExpanded, setIsProgramsExpanded] = useState(false);
  const [customProgramMode, setCustomProgramMode] = useState(false);
  const [customProgramData, setCustomProgramData] = useState({
    program_type: 'major',  // Default to major
    program_name: ''
  });
  const [formData, setFormData] = useState({
    department: '',
    courseNumber: '',
    courseName: '',
    term: ''
  });
  const [editingCourseId, setEditingCourseId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingPrograms, setLoadingPrograms] = useState(true);

  // Load user courses and programs on component mount and when modal opens
  useEffect(() => {
    if (isOpen) {
      loadUserCourses();
      loadUserPrograms();
      loadAvailablePrograms();
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

  // Function to load user programs
  const loadUserPrograms = async () => {
    try {
      setLoadingPrograms(true);
      const userPrograms = await getUserPrograms();
      setPrograms(userPrograms);
    } catch (error) {
      console.error('Error loading programs:', error);
      showNotification('Failed to load programs', false);
    } finally {
      setLoadingPrograms(false);
    }
  };

  // Function to load available program templates
  const loadAvailablePrograms = async () => {
    try {
      const programs = await getAvailablePrograms();
      setAvailablePrograms(programs);
    } catch (error) {
      console.error('Error loading available programs:', error);
      showNotification('Failed to load available programs', false);
    }
  };

  // Handle course form input change
  const handleChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [id]: value
    }));
  };

  // Handle program selection change
  const handleProgramChange = (e) => {
    setSelectedProgramId(e.target.value);
  };

  // Handle custom program data change
  const handleCustomProgramChange = (e) => {
    const { name, value } = e.target;
    setCustomProgramData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Toggle custom program mode
  const toggleCustomProgramMode = () => {
    setCustomProgramMode(!customProgramMode);
    if (customProgramMode) {
      // Reset fields when exiting custom mode
      setSelectedProgramId('');
    } else {
      // Reset custom program data when entering custom mode
      setCustomProgramData({
        program_type: 'major',
        program_name: ''
      });
    }
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

  // Handle add program from template
  const handleAddProgramFromTemplate = async () => {
    if (!selectedProgramId) {
      showNotification('Please select a program', false);
      return;
    }
    
    try {
      const newProgram = await assignProgramFromTemplate(selectedProgramId);
      
      // Add to local state
      setPrograms(prev => [...prev, newProgram]);
      
      // Clear selection
      setSelectedProgramId('');
      
      showNotification('Program added successfully');
    } catch (error) {
      console.error('Error adding program:', error);
      showNotification('Failed to add program', false);
    }
  };

  // Handle add custom program
  const handleAddCustomProgram = async () => {
    const { program_type, program_name } = customProgramData;
    
    if (!program_type || !program_name) {
      showNotification('Program type and name are required', false);
      return;
    }
    
    // Check if program name already exists
    if (programs.some(p => p.program_name === program_name)) {
      showNotification('A program with this name already exists', false);
      return;
    }
    
    try {
      const newProgram = await addCustomProgram(program_type, program_name);
      
      // Add to local state
      setPrograms(prev => [...prev, newProgram]);
      
      // Clear form
      setCustomProgramData({
        program_type: 'major',
        program_name: ''
      });
      
      showNotification('Custom program added successfully');
      
      // Exit custom program mode
      setCustomProgramMode(false);
    } catch (error) {
      console.error('Error adding custom program:', error);
      showNotification('Failed to add custom program', false);
    }
  };

  // Handle remove program
  const handleRemoveProgram = async (programName) => {
    if (!window.confirm('Are you sure you want to remove this program?')) {
      return;
    }
    
    try {
      await removeProgram(programName);
      
      // Remove from local state
      setPrograms(prev => prev.filter(program => program.program_name !== programName));
      
      showNotification('Program removed successfully');
    } catch (error) {
      console.error('Error removing program:', error);
      showNotification('Failed to remove program', false);
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
          <div id="program-management" className="program-management">
            <div 
              className="program-header"
              onClick={() => setIsProgramsExpanded(!isProgramsExpanded)}
            >
              <h3>
                <FontAwesomeIcon icon={faGraduationCap} style={{ marginRight: '10px' }} />
                Academic Programs
              </h3>
              <FontAwesomeIcon 
                icon={faChevronDown} 
                className={`chevron-icon ${isProgramsExpanded ? 'expanded' : ''}`}
              />
            </div>
            
            <div className={`program-content ${isProgramsExpanded ? 'expanded' : ''}`}>
              {!customProgramMode ? (
                // Program template selection mode
                <div className="program-select-container">
                  <div className="program-select-header">
                    <label htmlFor="program-select">Select a program template:</label>
                    <button 
                      className="toggle-custom-btn"
                      onClick={toggleCustomProgramMode}
                    >
                      Create Custom Program
                    </button>
                  </div>
                  
                  <div className="program-select-form">
                    <select 
                      id="program-select" 
                      className="program-select"
                      value={selectedProgramId}
                      onChange={handleProgramChange}
                    >
                      <option value="">Select a Program</option>
                      {availablePrograms.map((program) => (
                        <option key={program.id} value={program.id}>
                          {program.program_name} ({program.program_type})
                        </option>
                      ))}
                    </select>
                    
                    <button 
                      className="add-program-btn"
                      onClick={handleAddProgramFromTemplate}
                      disabled={!selectedProgramId}
                    >
                      <FontAwesomeIcon icon={faPlus} />
                      Add Program
                    </button>
                  </div>
                </div>
              ) : (
                // Custom program form
                <div className="custom-program-container">
                  <div className="custom-program-header">
                    <h4>Create Custom Program</h4>
                    <button 
                      className="toggle-custom-btn"
                      onClick={toggleCustomProgramMode}
                    >
                      Use Program Template
                    </button>
                  </div>
                  
                  <div className="custom-program-form">
                    <div className="form-group">
                      <label htmlFor="program_type">Program Type</label>
                      <select
                        id="program_type"
                        name="program_type"
                        value={customProgramData.program_type}
                        onChange={handleCustomProgramChange}
                      >
                        <option value="major">Major</option>
                        <option value="minor">Minor</option>
                        <option value="certificate">Certificate</option>
                        <option value="concentration">Concentration</option>
                      </select>
                    </div>
                    
                    <div className="form-group">
                      <label htmlFor="program_name">Program Name</label>
                      <input
                        type="text"
                        id="program_name"
                        name="program_name"
                        value={customProgramData.program_name}
                        onChange={handleCustomProgramChange}
                        placeholder="e.g., Computer Science"
                        required
                      />
                    </div>
                    
                    <button
                      className="add-custom-program-btn"
                      onClick={handleAddCustomProgram}
                      disabled={!customProgramData.program_name || !customProgramData.program_type}
                    >
                      <FontAwesomeIcon icon={faPlus} />
                      Add Custom Program
                    </button>
                  </div>
                </div>
              )}
              
              <h4>Your Academic Programs:</h4>
              <div className="program-list">
                {loadingPrograms ? (
                  <div className="no-programs-message">Loading programs...</div>
                ) : programs.length === 0 ? (
                  <div className="no-programs-message">You haven't added any programs yet.</div>
                ) : (
                  programs.map(program => (
                    <ProgramItem 
                      key={program.id}
                      program={program}
                      onRemove={handleRemoveProgram}
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
                        <option value="Fall 2024">Fall 2024</option>
                        <option value="Spring 2024">Spring 2024</option>
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
import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faPlus, 
  faBuildingColumns, 
  faHashtag, 
  faCalendar, 
  faBook 
} from '@fortawesome/free-solid-svg-icons';

import Navbar from '../components/Navbar';
import CourseItem from '../components/CourseItem';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { 
  getUserCourses, 
  addCourse, 
  removeCourse, 
  updateCourse 
} from '../services/courseService';

const ClassManagement = () => {
  const { currentUser } = useAuth();
  const { showNotification } = useNotification();
  
  const [courses, setCourses] = useState([]);
  const [formData, setFormData] = useState({
    department: '',
    courseNumber: '',
    courseName: '',
    term: ''
  });
  const [editingCourseId, setEditingCourseId] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load user courses on component mount
  useEffect(() => {
    loadUserCourses();
  }, []);

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

  // Handle form input change
  const handleChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [id]: value
    }));
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

  return (
    <>
      <Navbar />
      <div className="container">
        <h2>Class Management</h2>
        <p>Major: <span id="major-display">{currentUser?.major}</span></p>
        
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
                    <FontAwesomeIcon icon={faBuildingColumns} className="input-icon" />
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
                    <FontAwesomeIcon icon={faHashtag} className="input-icon" />
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
                    <FontAwesomeIcon icon={faCalendar} className="input-icon" />
                    <select 
                      id="term"
                      value={formData.term}
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
              </div>
              
              <div className="form-group">
                <label htmlFor="courseName">Course Name</label>
                <div className="input-wrapper">
                  <FontAwesomeIcon icon={faBook} className="input-icon" />
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
    </>
  );
};

export default ClassManagement;
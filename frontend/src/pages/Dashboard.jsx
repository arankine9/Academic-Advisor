import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBookOpen, faComments } from '@fortawesome/free-solid-svg-icons';
import { useAuth } from '../context/AuthContext';
import { getUserCourses } from '../services/courseService';
import { useNotification } from '../context/NotificationContext';
import Navbar from '../components/Navbar';

const Dashboard = () => {
  const { currentUser } = useAuth();
  const { showNotification } = useNotification();
  const [courseCount, setCourseCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Load dashboard data on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const courses = await getUserCourses();
        setCourseCount(courses.length);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        showNotification('Failed to load data', false);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [showNotification]);

  return (
    <>
      <Navbar />
      <div className="container">
        <h2>Welcome to Your Academic Dashboard</h2>
        <p>Major: <span id="major-display">{currentUser?.major}</span></p>
        
        <div className="dashboard-summary">
          <h3>Your Academic Progress</h3>
          <span 
            className="stats-number" 
            id="course-count"
            style={{
              opacity: loading ? 0 : 1,
              transform: loading ? 'translateY(20px)' : 'translateY(0)',
              transition: 'opacity 0.6s ease, transform 0.6s ease'
            }}
          >
            {courseCount}
          </span>
          <p style={{ textAlign: 'center' }}>Courses Completed</p>
          
          <div style={{ marginTop: '20px' }}>
            <p>Track your academic journey and get personalized recommendations.</p>
            <p>Keep your course list updated to receive the most accurate guidance for your degree path.</p>
          </div>
        </div>
        
        <div className="dashboard-actions">
          <h3>Quick Actions</h3>
          <div className="action-buttons">
            <button onClick={() => navigate('/classes')}>
              <FontAwesomeIcon icon={faBookOpen} style={{ marginRight: '8px' }} />
              Manage My Classes
            </button>
            <button onClick={() => navigate('/advising')}>
              <FontAwesomeIcon icon={faComments} style={{ marginRight: '8px' }} />
              Get Course Recommendations
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Dashboard;
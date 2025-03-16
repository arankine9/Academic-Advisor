import React, { useState } from 'react';
import './CourseRecommendation.css';

const CourseRecommendation = ({ courseData }) => {
  const [expanded, setExpanded] = useState(false);

  // Safety check for missing or malformed data
  if (!courseData || typeof courseData !== 'object') {
    console.error('Invalid course data provided to CourseRecommendation:', courseData);
    return (
      <div className="course-card error">
        <div className="course-header">
          <div className="course-title">
            <span className="course-code">Error</span>
            <span className="course-name">Invalid course data</span>
          </div>
        </div>
      </div>
    );
  }

  const toggleExpand = () => {
    setExpanded(!expanded);
  };

  // Format availability information with safety checks
  const availabilityText = courseData.availability && 
    courseData.availability.available_seats !== undefined && 
    courseData.availability.total_seats !== undefined ?
      `${courseData.availability.available_seats}/${courseData.availability.total_seats} seats available` : 
      'Availability unknown';

  // Format schedule information with safety checks
  const scheduleText = courseData.schedule && 
    courseData.schedule.days && 
    courseData.schedule.time ?
      `${courseData.schedule.days} at ${courseData.schedule.time}` : 
      'Schedule to be announced';

  return (
    <div className="course-card">
      <div className="course-header" onClick={toggleExpand}>
        <div className="course-title">
          <span className="course-code">{courseData.course_code}</span>
          <span className="course-name">{courseData.course_name}</span>
        </div>
        <div className="course-credits">{courseData.credits} credits</div>
        <div className="expand-icon">{expanded ? '▼' : '▶'}</div>
      </div>
      
      <div className="course-basic-info">
        <div className="course-schedule">
          <span className="info-label">Schedule:</span> {scheduleText}
        </div>
        <div className="course-location">
          <span className="info-label">Location:</span> {courseData.location}
        </div>
        <div className="course-instructor">
          <span className="info-label">Instructor:</span> {courseData.instructor}
        </div>
        <div className="course-availability">
          <span className="info-label">Availability:</span> {availabilityText}
        </div>
      </div>
      
      {expanded && (
        <div className="course-details">
          <div className="course-description">
            <h4>Description</h4>
            <p>{courseData.description || 'No description available'}</p>
          </div>
          
          {courseData.prerequisites && (
            <div className="course-prerequisites">
              <h4>Prerequisites</h4>
              <p>{courseData.prerequisites}</p>
            </div>
          )}
          
          <div className="course-crn">
            <span className="info-label">CRN:</span> {courseData.crn || 'N/A'}
          </div>
        </div>
      )}
    </div>
  );
};

export default CourseRecommendation;
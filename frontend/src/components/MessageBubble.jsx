import React from 'react';
import CourseRecommendation from './CourseRecommendation';

const MessageBubble = ({ message, isUser }) => {
  // Handle null or undefined messages
  if (message === null || message === undefined) {
    console.warn('Received null or undefined message in MessageBubble');
    return null;
  }
  
  // Format message paragraphs for text content
  const formatTextContent = (text) => {
    if (!text) return [<p key="empty">...</p>];
    
    return text.split('\n').map((line, index) => 
      line.trim() ? <p key={index}>{line}</p> : null
    ).filter(Boolean);
  };

  // Handle normal text messages (both user and non-course advisor messages)
  if (isUser || typeof message === 'string') {
    const messageContent = typeof message === 'string' ? message : JSON.stringify(message);
    
    return (
      <div className={`chat-message message-appear ${isUser ? 'user-message' : 'advisor-message'}`}>
        <div className="message-content">
          {formatTextContent(messageContent)}
        </div>
      </div>
    );
  }
  
  // Handle course recommendation objects
  if (typeof message === 'object' && message.type === 'course_recommendations') {
    return (
      <div className="chat-message-container">
        {/* Render conversational message first */}
        <div className="chat-message message-appear advisor-message">
          <div className="message-content">
            {formatTextContent(message.message)}
          </div>
        </div>
        
        {/* Render course recommendations */}
        <div className="course-recommendations-container">
          {message.course_data.map((course, index) => (
            <CourseRecommendation key={index} courseData={course} />
          ))}
        </div>
      </div>
    );
  }
  
  // Fallback for any other type of content
  return (
    <div className={`chat-message message-appear advisor-message`}>
      <div className="message-content">
        <p>{typeof message === 'string' ? message : JSON.stringify(message)}</p>
      </div>
    </div>
  );
};

export default MessageBubble;
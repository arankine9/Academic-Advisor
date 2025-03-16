import React, { useState, useRef, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane } from '@fortawesome/free-solid-svg-icons';
import { faTwitter, faInstagram, faTiktok } from '@fortawesome/free-brands-svg-icons';

import MessageBubble from './MessageBubble';
import CourseRecommendation from './CourseRecommendation';
import TypingIndicator from './TypingIndicator';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { sendMessage } from '../services/advisingService';
import './AdvisingChat.css';
import './CourseRecommendation.css';

const AdvisingChat = () => {
  const { currentUser } = useAuth();
  const { showNotification } = useNotification();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Debug logging for message state changes
  useEffect(() => {
    console.log('Messages state updated:', messages);
  }, [messages]);

  // With column-reverse layout, we don't need to scroll to bottom anymore
  // as new messages will appear at the bottom automatically
  useEffect(() => {
    // We'll keep this for compatibility, but with column-reverse it's less necessary
    if (messagesEndRef.current && messages.length <= 2) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  // Focus input field on component mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  // Handle input change
  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  // Handle sending message
  const handleSendMessage = async () => {
    const message = inputValue.trim();
    
    if (!message || isWaitingForResponse) {
      return;
    }
    
    // Debug log before sending
    console.log('Sending message to API:', message);
    
    // Add user message to chat
    setMessages(prev => [...prev, { content: message, isUser: true }]);
    
    // Clear input field
    setInputValue('');
    
    // Set waiting state
    setIsWaitingForResponse(true);
    
    try {
      // Send message to API
      const response = await sendMessage(message);
      console.log('Raw API response:', response);
      console.log('Response structure:', JSON.stringify(response, null, 2));
      
      if (response && response.response) {
        // Add response to chat (can be either string or object)
        setMessages(prev => [...prev, { content: response.response, isUser: false }]);
      } else {
        // Handle unexpected response format
        console.error('Unexpected response format:', response);
        setMessages(prev => [...prev, {
          content: "I received an unexpected response format. Please try again.",
          isUser: false
        }]);
      }
      
      // Reset waiting state
      setIsWaitingForResponse(false);
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message to chat
      setMessages(prev => [...prev, {
        content: "I'm sorry, I encountered an error. Please try again later.",
        isUser: false
      }]);
      
      // Show notification
      showNotification('Failed to send message', false);
      
      // Reset waiting state
      setIsWaitingForResponse(false);
    }
  };

  // Handle key press (Enter to send)
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="GradPath-container">
      {/* Header */}
      <header className="GradPath-header">
        <div className="header-left-section">
          {/* Empty left section */}
        </div>
        <div className="header-center-section">
          {/* Empty center - removed Academic Advisor */}
        </div>
        <div className="header-right-section">
          <div className="brand">GradPath</div>
        </div>
      </header>

      {/* Main Content */}
      <main className="GradPath-main">
        {/* Always show tagline regardless of messages */}
        <h1 className="GradPath-tagline">Plan for your future. Today.</h1>
        
        {/* Chat messages */}
        <div className="chat-messages-container">
          {/* With column-reverse, elements at the beginning of the DOM appear at the bottom visually */}
          
          {/* Typing indicator should appear at the bottom (beginning of DOM with column-reverse) */}
          {isWaitingForResponse && <TypingIndicator />}
          
          {/* Invisible element for scrolling to bottom */}
          <div ref={messagesEndRef} />
          
          {/* Render messages in reverse order to work with column-reverse layout */}
          {[...messages].reverse().map((msg, index) => (
            <MessageBubble 
              key={messages.length - 1 - index} 
              message={msg.content} 
              isUser={msg.isUser} 
            />
          ))}
        </div>
        
        {/* Input area */}
        <div className="GradPath-input-container">
          <div className="GradPath-input-wrapper">
            <textarea
              className="GradPath-input-field"
              placeholder="Type your message here..."
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyPress}
              disabled={isWaitingForResponse}
              ref={inputRef}
              rows={inputValue.split('\n').length || 1}
            />
            <button 
              className={`send-btn ${inputValue.trim() ? 'active' : ''}`}
              onClick={handleSendMessage}
              disabled={isWaitingForResponse || !inputValue.trim()}
            >
              <FontAwesomeIcon icon={faPaperPlane} />
            </button>
          </div>
        </div>
      </main>
      
      {/* Footer */}
      <footer className="GradPath-footer">
        <div className="social-icons">
          <FontAwesomeIcon icon={faTwitter} />
          <FontAwesomeIcon icon={faInstagram} />
          <FontAwesomeIcon icon={faTiktok} />
        </div>
        <div className="privacy-policy">
          PRIVACY POLICY
        </div>
      </footer>
    </div>
  );
};

export default AdvisingChat;
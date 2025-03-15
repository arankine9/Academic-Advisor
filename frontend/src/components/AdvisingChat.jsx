import React, { useState, useRef, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane, faCog, faArrowRight, faMoon, faSun } from '@fortawesome/free-solid-svg-icons';
import { faTwitter, faInstagram, faTiktok } from '@fortawesome/free-brands-svg-icons';

import MessageBubble from '../components/MessageBubble';
import TypingIndicator from '../components/TypingIndicator';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { sendMessage } from '../services/advisingService';
import './AdvisingChat.css';

const AdvisingChat = () => {
  const { currentUser } = useAuth();
  const { showNotification } = useNotification();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [activeDot, setActiveDot] = useState(0); // For pagination dots
  const [darkMode, setDarkMode] = useState(
    localStorage.getItem('gradpath-dark-mode') === 'true'
  );
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Load dark mode from localStorage on component mount
  useEffect(() => {
    // Apply dark mode class to document on initial load
    if (darkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, []);

  // Toggle dark mode
  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('gradpath-dark-mode', newDarkMode);
    
    if (newDarkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  };

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
    
    // Add user message to chat
    setMessages(prev => [...prev, { content: message, isUser: true }]);
    
    // Clear input field
    setInputValue('');
    
    // Set waiting state
    setIsWaitingForResponse(true);
    
    try {
      // Send message to API
      const response = await sendMessage(message);
      
      // Add advisor response to chat
      setMessages(prev => [...prev, { content: response.response, isUser: false }]);
      
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
    <div className={`GradPath-container ${darkMode ? 'dark-mode' : ''}`}>
      {/* Header */}
      <header className="GradPath-header">
        <div className="header-left-section">
          <button className="dark-mode-toggle" onClick={toggleDarkMode} aria-label="Toggle dark mode">
            <FontAwesomeIcon icon={darkMode ? faSun : faMoon} />
          </button>
        </div>
        <div className="header-right-section">
          <div className="brand">GradPath</div>
        </div>
      </header>

      {/* Main Content */}
      <main className={`GradPath-main ${messages.length > 0 ? 'has-messages' : ''}`}>
        {/* Icon and description - Only show when no messages exist */}
        {messages.length === 0 && (
          <div className="GradPath-intro">
            <h1 className="GradPath-tagline">Plan for your future. Today.</h1>
          </div>
        )}
        
        {/* Chat messages */}
        {messages.length > 0 && (
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
        )}
        
        {/* Input area */}
        <div className="GradPath-input-container">
          <div className="GradPath-input-wrapper">
            <textarea
              className="GradPath-input-field"
              placeholder={messages.length === 0 ? "Hello! I'm your academic advisor. Let's plan your courses" : ""}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyPress}
              disabled={isWaitingForResponse}
              ref={inputRef}
              rows={inputValue.split('\n').length || 1}
            />
            <button 
              className="send-btn"
              onClick={handleSendMessage}
              disabled={isWaitingForResponse}
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
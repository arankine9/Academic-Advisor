import React, { useState, useRef, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane, faGraduationCap } from '@fortawesome/free-solid-svg-icons';
import { faTwitter, faInstagram, faTiktok } from '@fortawesome/free-brands-svg-icons';

import MessageBubble from './MessageBubble';
import CourseRecommendation from './CourseRecommendation';
import TypingIndicator from './TypingIndicator';
import ClassManagementModal from './ClassManagementModal'; // Added component
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { sendMessage, checkPendingResponse } from '../services/advisingService';
import './AdvisingChat.css';
import './CourseRecommendation.css';

const AdvisingChat = () => {
  const { currentUser } = useAuth();
  const { showNotification } = useNotification();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false); // Added state
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const pollTimerRef = useRef(null);

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

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, []);

  // Open class management modal - Added from Version 2
  const openModal = () => {
    setIsModalOpen(true);
    // Prevent body scrolling when modal is open
    document.body.style.overflow = 'hidden';
  };

  // Close class management modal - Added from Version 2
  const closeModal = () => {
    setIsModalOpen(false);
    // Restore body scrolling when modal is closed
    document.body.style.overflow = 'auto';
  };

  // Start polling for response
  const startPollingForResponse = () => {
    setIsPolling(true);
    let pollCount = 0;
    const maxPolls = 30; // Stop after 30 attempts (30 seconds)
    
    pollTimerRef.current = setInterval(async () => {
      try {
        pollCount++;
        
        const pendingResponse = await checkPendingResponse();
        
        if (pendingResponse && pendingResponse.response && !pendingResponse.pending) {
          // Got a response, stop polling
          clearInterval(pollTimerRef.current);
          setIsPolling(false);
          
          // Add response to messages
          setMessages(prev => [...prev, { 
            content: pendingResponse.response, 
            isUser: false 
          }]);
          
          // Reset waiting state
          setIsWaitingForResponse(false);
        } else if (pollCount >= maxPolls) {
          // Timeout after 30 seconds
          clearInterval(pollTimerRef.current);
          setIsPolling(false);
          setIsWaitingForResponse(false);
          
          // Add timeout message
          setMessages(prev => [...prev, {
            content: "I'm taking longer than expected. Please try again or rephrase your question.",
            isUser: false
          }]);
          
          showNotification('Request timed out', false);
        }
      } catch (error) {
        console.error('Error checking pending response:', error);
        
        clearInterval(pollTimerRef.current);
        setIsPolling(false);
        setIsWaitingForResponse(false);
        
        showNotification('Failed to check response status', false);
      }
    }, 1000); // Check every second
  };

  // Handle input change
  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  // Handle sending message
  const handleSendMessage = async () => {
    const message = inputValue.trim();
    
    if (!message || isWaitingForResponse || isPolling) {
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
      
      if (response && response.response) {
        if (response.processing === true) {
          // This is an acknowledgment message, start polling for final response
          setMessages(prev => [...prev, { 
            content: response.response, 
            isUser: false,
            isAcknowledgment: true
          }]);
          
          // Start polling for the full response
          startPollingForResponse();
        } else {
          // This is a final response (for general conversation)
          setMessages(prev => [...prev, { content: response.response, isUser: false }]);
          setIsWaitingForResponse(false);
        }
      } else {
        handleErrorResponse("Unexpected response format");
      }
    } catch (error) {
      handleErrorResponse(`Failed to send message: ${error.message}`);
    }
  };

  const handleErrorResponse = (errorMessage) => {
    console.error(errorMessage);
    
    // Add error message to chat
    setMessages(prev => [...prev, {
      content: "I'm sorry, I encountered an error. Please try again later.",
      isUser: false
    }]);
    
    // Show notification
    showNotification(errorMessage, false);
    
    // Reset waiting state
    setIsWaitingForResponse(false);
    setIsPolling(false);
    
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
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
          {/* Added manage classes button */}
          <button className="manage-classes-btn" onClick={openModal}>
            <FontAwesomeIcon icon={faGraduationCap} className="btn-icon" />
            <span>Manage Classes</span>
          </button>
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
      
      {/* Added class management modal */}
      <ClassManagementModal 
        isOpen={isModalOpen} 
        onClose={closeModal} 
      />
    </div>
  );
};

export default AdvisingChat;
import React, { useState, useRef, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane } from '@fortawesome/free-solid-svg-icons';

import Navbar from '../components/Navbar';
import MessageBubble from '../components/MessageBubble';
import TypingIndicator from '../components/TypingIndicator';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { sendMessage } from '../services/advisingService';

const AdvisingChat = () => {
  const { currentUser } = useAuth();
  const { showNotification } = useNotification();
  const [messages, setMessages] = useState([
    {
      content: "Hello! I'm your academic advisor. I can help you plan your courses based on your academic history.\n\nYou can ask me questions like \"What classes should I take next?\" or \"What are the prerequisites for CS 310?\"",
      isUser: false
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // Focus input field on component mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  // Function to scroll to bottom of chat
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

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
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  return (
    <>
      <Navbar />
      <div className="container">
        <h2>Academic Advising</h2>
        <p>Major: <span id="major-display">{currentUser?.major}</span></p>
        
        <div id="chat-section">
          <div className="chat-container" id="chat-messages">
            {/* Render messages */}
            {messages.map((msg, index) => (
              <MessageBubble 
                key={index} 
                message={msg.content} 
                isUser={msg.isUser} 
              />
            ))}
            
            {/* Typing indicator */}
            {isWaitingForResponse && <TypingIndicator />}
            
            {/* Invisible element for scrolling to bottom */}
            <div ref={messagesEndRef} />
          </div>
          
          <div className="chat-input">
            <input 
              type="text" 
              id="chat-input-field" 
              placeholder="Ask a question..." 
              value={inputValue}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              disabled={isWaitingForResponse}
              ref={inputRef}
            />
            <button 
              id="send-message-btn" 
              onClick={handleSendMessage}
              disabled={isWaitingForResponse}
            >
              <FontAwesomeIcon icon={faPaperPlane} style={{ marginRight: '8px' }} />
              Send
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default AdvisingChat;
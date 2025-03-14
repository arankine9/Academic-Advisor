import React from 'react';

const MessageBubble = ({ message, isUser }) => {
  // Format message paragraphs
  const formattedContent = message.split('\n').map((line, index) => 
    line.trim() ? <p key={index}>{line}</p> : null
  ).filter(Boolean);

  return (
    <div className={`chat-message ${isUser ? 'user-message' : 'advisor-message'}`}>
      {formattedContent}
    </div>
  );
};

export default MessageBubble;
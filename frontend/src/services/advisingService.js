

import api from './authService';

// Send message to advisor
export const sendMessage = async (message) => {
  const response = await api.post('/advising', {
    message
  });
  return response.data;
};

export default {
  sendMessage
};
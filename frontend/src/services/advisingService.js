import api from './authService';

// Send message to advisor
export const sendMessage = async (message) => {
  const response = await api.post('/advising', {
    message
  });
  return response.data;
};

export const checkPendingResponse = async () => {
  const response = await api.get('/advising/pending');
  return response.data;
};

export default {
  sendMessage,
  checkPendingResponse
};




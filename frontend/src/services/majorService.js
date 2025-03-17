import api from './authService';

// Get available majors for selection
export const getAvailableMajors = async () => {
  const response = await api.get('/majors/available');
  return response.data;
};

// Get user's majors
export const getUserMajors = async () => {
  const response = await api.get('/majors/me');
  return response.data;
};

// Add major to user
export const addMajor = async (majorName) => {
  const response = await api.post('/majors', {
    name: majorName
  });
  return response.data;
};

// Remove major from user
export const removeMajor = async (majorId) => {
  const response = await api.delete(`/majors/${majorId}`);
  return response.data;
};

export default {
  getAvailableMajors,
  getUserMajors,
  addMajor,
  removeMajor
}; 
import api from './authService';

// Get available program templates
export const getAvailablePrograms = async () => {
  const response = await api.get('/programs/available');
  return response.data;
};

// Get user's programs
export const getUserPrograms = async () => {
  const response = await api.get('/programs/me');
  return response.data;
};

// Add program to user from template
export const assignProgram = async (programId) => {
  const response = await api.post('/programs', {
    program_id: programId
  });
  return response.data;
};

// Remove program from user
export const removeProgram = async (programName) => {
  const response = await api.delete(`/programs/${programName}`);
  return response.data;
};

// Get program progress
export cons
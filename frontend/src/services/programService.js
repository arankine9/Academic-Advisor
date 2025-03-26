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
export const assignProgramFromTemplate = async (programId) => {
  const response = await api.post('/programs', {
    program_id: programId
  });
  return response.data;
};

// Add custom program to user
export const addCustomProgram = async (programType, programName, requiredCourses = []) => {
  const response = await api.post('/programs', {
    program_type: programType,
    program_name: programName,
    required_courses: requiredCourses
  });
  return response.data;
};

// Remove program from user
export const removeProgram = async (programName) => {
  const response = await api.delete(`/programs/${programName}`);
  return response.data;
};

// Get program progress
export const getProgramProgress = async () => {
  const response = await api.get('/programs/progress');
  return response.data;
};

export default {
  getAvailablePrograms,
  getUserPrograms,
  assignProgramFromTemplate,
  addCustomProgram,
  removeProgram,
  getProgramProgress
};
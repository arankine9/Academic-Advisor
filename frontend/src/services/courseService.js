import api from './authService';

// Get user courses
export const getUserCourses = async () => {
  const response = await api.get('/courses/me');
  return response.data;
};

// Add course
export const addCourse = async (department, courseNumber, courseName, term) => {
  const response = await api.post('/courses', {
    department,
    course_number: courseNumber,
    name: courseName,
    term
  });
  return response.data;
};

// Remove course
export const removeCourse = async (courseId) => {
  const response = await api.delete(`/courses/${courseId}`);
  return response.data;
};

// Update course
export const updateCourse = async (courseId, courseData) => {
  const response = await api.put(`/courses/${courseId}`, courseData);
  return response.data;
};

// Get recommendations
export const getRecommendations = async () => {
  const response = await api.get('/advising');
  return response.data;
};

export default {
  getUserCourses,
  addCourse,
  removeCourse,
  updateCourse,
  getRecommendations
};
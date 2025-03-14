import axios from 'axios';

// No need for dynamic API_URL - it's always relative in production
const API_URL = '/api';

// Create axios instance with base URL
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add authorization header to requests if token exists
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Login user
export const loginUser = async (username, password) => {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);

  const response = await axios.post(`${API_URL}/token`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Register user
export const registerUser = async (username, email, password, major) => {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('email', email);
  formData.append('password', password);
  formData.append('major', major);

  const response = await axios.post(`${API_URL}/register`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Get current user
export const getCurrentUser = async () => {
  const response = await api.get('/users/me');
  return response.data;
};

export default api;
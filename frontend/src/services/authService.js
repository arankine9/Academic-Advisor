import { auth } from '../firebase/config';
import { doc, getDoc, getFirestore } from 'firebase/firestore';

// Initialize Firestore
const db = getFirestore();

// Create axios instance for non-auth API calls
import axios from 'axios';

const API_URL = '/api';
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Update interceptor to use Firebase token
api.interceptors.request.use(
  async (config) => {
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken();
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Get current user data from Firestore
export const getCurrentUser = async () => {
  const user = auth.currentUser;
  
  if (!user) {
    throw new Error('User not authenticated');
  }
  
  try {
    const userDoc = await getDoc(doc(db, "Users", user.email));
    
    if (userDoc.exists()) {
      return {
        uid: user.uid,
        email: user.email,
        ...userDoc.data()
      };
    } else {
      return {
        uid: user.uid,
        email: user.email
      };
    }
  } catch (error) {
    console.error("Error fetching user data:", error);
    throw error;
  }
};

// For API calls that don't involve authentication
export default api;
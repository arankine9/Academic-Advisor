import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged 
} from 'firebase/auth';
import { doc, setDoc, getDoc } from 'firebase/firestore';
import { auth } from '../firebase/config';
import { getFirestore } from 'firebase/firestore';

// Initialize Firestore
const db = getFirestore();

// Create a context for authentication
const AuthContext = createContext();

// Hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};

// Provider component
export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Listen for auth state changes on initial load
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        // Get additional user data from Firestore
        try {
          const userDoc = await getDoc(doc(db, "Users", user.email));
          if (userDoc.exists()) {
            setCurrentUser({
              uid: user.uid,
              email: user.email,
              ...userDoc.data()
            });
          } else {
            // If user exists in Auth but not in Firestore, create the document
            await setDoc(doc(db, "Users", user.email), {
              email: user.email,
              academic_level: 'undergraduate',
              created_at: new Date()
            });
            
            setCurrentUser({
              uid: user.uid,
              email: user.email,
              academic_level: 'undergraduate',
              created_at: new Date()
            });
          }
        } catch (err) {
          console.error("Error fetching user data:", err);
          setCurrentUser({
            uid: user.uid,
            email: user.email
          });
        }
      } else {
        setCurrentUser(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // Login function
  const login = async (email, password) => {
    try {
      setError(null);
      await signInWithEmailAndPassword(auth, email, password);
      return true;
    } catch (error) {
      const errorMessages = {
        'auth/invalid-email': 'Invalid email format',
        'auth/user-disabled': 'This account has been disabled',
        'auth/user-not-found': 'No account found with this email',
        'auth/wrong-password': 'Incorrect password',
        'auth/too-many-requests': 'Too many failed login attempts. Try again later',
      };

      setError(errorMessages[error.code] || error.message || 'Login failed');
      return false;
    }
  };

  // Register function
  const register = async (email, password) => {
    try {
      setError(null);
      
      // Create user in Firebase Authentication
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;
      
      // Create user document in Firestore
      await setDoc(doc(db, "Users", email), {
        email: email,
        academic_level: 'undergraduate',
        created_at: new Date(),
        uid: user.uid
      });
      
      return true;
    } catch (error) {
      const errorMessages = {
        'auth/email-already-in-use': 'Email already registered',
        'auth/invalid-email': 'Invalid email format',
        'auth/weak-password': 'Password is too weak',
        'auth/operation-not-allowed': 'Email/password accounts are not enabled'
      };

      setError(errorMessages[error.code] || error.message || 'Registration failed');
      return false;
    }
  };

  // Logout function
  const logout = async () => {
    try {
      await signOut(auth);
      navigate('/');
    } catch (error) {
      console.error("Error signing out:", error);
    }
  };

  // Value object to be provided by context
  const value = {
    currentUser,
    login,
    register,
    logout,
    error,
    setError,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
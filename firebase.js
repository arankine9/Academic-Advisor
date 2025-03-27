

import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getAnalytics } from 'firebase/analytics';

// Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyDam8lV-5VxmatuUW1uF3u09V6G21LIbKs",
    authDomain: "gradpath-1ffff.firebaseapp.com",
    projectId: "gradpath-1ffff",
    storageBucket: "gradpath-1ffff.firebasestorage.app",
    messagingSenderId: "174070836359",
    appId: "1:174070836359:web:914b2f1e5a2760a4d21c22",
    measurementId: "G-WBPVF75RJJ"
  };

// Initialize Firebase
const app = initializeApp(firebaseConfig);
// Initialize Firebase Analytics
const analytics = getAnalytics(app);
// Initialize Firebase Authentication
const auth = getAuth(app);

export { auth };

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faUser, faLock, faEnvelope, faGraduationCap } from '@fortawesome/free-solid-svg-icons';
import { getAvailablePrograms } from '../services/programService';

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    programId: '' // Changed from 'major' to 'programId'
  });
  const [availablePrograms, setAvailablePrograms] = useState([]);
  const [registerSuccess, setRegisterSuccess] = useState('');
  const [loadingPrograms, setLoadingPrograms] = useState(false);
  const { login, register, error, currentUser } = useAuth();
  const navigate = useNavigate();

  // Redirect to dashboard if already logged in
  useEffect(() => {
    if (currentUser) {
      navigate('/dashboard');
    }
  }, [currentUser, navigate]);

  // Fetch available programs on component mount and when switching to register form
  useEffect(() => {
    if (!isLogin) {
      fetchAvailablePrograms();
    }
  }, [isLogin]);

  // Fetch available programs
  const fetchAvailablePrograms = async () => {
    try {
      setLoadingPrograms(true);
      const programs = await getAvailablePrograms();
      setAvailablePrograms(programs);
      // Set the first program as default if available
      if (programs.length > 0 && !formData.programId) {
        setFormData(prev => ({
          ...prev,
          programId: programs[0].id
        }));
      }
    } catch (error) {
      console.error('Failed to fetch available programs:', error);
    } finally {
      setLoadingPrograms(false);
    }
  };

  // Handle form input change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (isLogin) {
      // Handle login
      const success = await login(formData.username, formData.password);
      if (success) {
        navigate('/dashboard');
      }
    } else {
      // Handle registration
      const success = await register(
        formData.username, 
        formData.email, 
        formData.password, 
        formData.programId // Changed from formData.major
      );
      
      if (success) {
        setRegisterSuccess('Registration successful! You can now login.');
        // Reset form
        setFormData({
          username: '',
          email: '',
          password: '',
          programId: availablePrograms.length > 0 ? availablePrograms[0].id : ''
        });
        
        // Switch to login after 2 seconds
        setTimeout(() => {
          setIsLogin(true);
          setRegisterSuccess('');
        }, 2000);
      }
    }
  };

  // Switch between login and register forms
  const switchForm = () => {
    setIsLogin(!isLogin);
    setRegisterSuccess('');
  };

  return (
    <div className="auth-wrapper">
      <div id="auth-section" className="container">
        <div className="logo-container">
          <h1>GradPath</h1>
          <p className="form-subtitle">Your academic journey starts here</p>
        </div>
        
        {/* Login Form */}
        {isLogin ? (
          <div id="login-section" className="auth-form">
            <h3 className="form-title">Welcome Back</h3>
            <form id="login-form" onSubmit={handleSubmit}>
              <div className="input-wrapper">
                <FontAwesomeIcon icon={faUser} className="input-icon" />
                <label htmlFor="login-username">Username</label>
                <input 
                  type="text" 
                  id="login-username" 
                  name="username" 
                  value={formData.username}
                  onChange={handleChange}
                  required 
                />
              </div>
              
              <div className="input-wrapper">
                <FontAwesomeIcon icon={faLock} className="input-icon" />
                <label htmlFor="login-password">Password</label>
                <input 
                  type="password" 
                  id="login-password" 
                  name="password" 
                  value={formData.password}
                  onChange={handleChange}
                  required 
                />
              </div>
              
              <button type="submit">Login</button>
              {error && <p id="login-error" className="error-message">{error}</p>}
              
              <div className="form-footer">
                <p>New user? <a href="#" className="form-link" onClick={(e) => { e.preventDefault(); switchForm(); }}><span>Sign up</span></a></p>
              </div>
            </form>
          </div>
        ) : (
          <div id="register-section" className="auth-form">
            <h3 className="form-title">Create Account</h3>
            <form id="register-form" onSubmit={handleSubmit}>
              <div className="input-wrapper">
                <FontAwesomeIcon icon={faUser} className="input-icon" />
                <label htmlFor="register-username">Username</label>
                <input 
                  type="text" 
                  id="register-username" 
                  name="username" 
                  value={formData.username}
                  onChange={handleChange}
                  required 
                />
              </div>
              
              <div className="input-wrapper">
                <FontAwesomeIcon icon={faEnvelope} className="input-icon" />
                <label htmlFor="register-email">Email</label>
                <input 
                  type="email" 
                  id="register-email" 
                  name="email" 
                  value={formData.email}
                  onChange={handleChange}
                  required 
                />
              </div>
              
              <div className="input-wrapper">
                <FontAwesomeIcon icon={faLock} className="input-icon" />
                <label htmlFor="register-password">Password</label>
                <input 
                  type="password" 
                  id="register-password" 
                  name="password" 
                  value={formData.password}
                  onChange={handleChange}
                  required 
                />
              </div>
              
              <div className="input-wrapper">
                <FontAwesomeIcon icon={faGraduationCap} className="input-icon" />
                <label htmlFor="register-program">Academic Program</label>
                {loadingPrograms ? (
                  <select 
                    id="register-program"
                    name="programId"
                    disabled
                  >
                    <option>Loading programs...</option>
                  </select>
                ) : (
                  <select 
                    id="register-program" 
                    name="programId" 
                    value={formData.programId}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select a program</option>
                    {availablePrograms.map(program => (
                      <option key={program.id} value={program.id}>
                        {program.program_name} ({program.program_type})
                      </option>
                    ))}
                  </select>
                )}
              </div>
              
              <button type="submit">Create Account</button>
              {error && <p id="register-error" className="error-message">{error}</p>}
              {registerSuccess && <p id="register-success" className="success-message">{registerSuccess}</p>}
              
              <div className="form-footer">
                <p>Already have an account? <a href="#" className="form-link" onClick={(e) => { e.preventDefault(); switchForm(); }}><span>Log in</span></a></p>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};

export default Login;
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLock, faEnvelope } from '@fortawesome/free-solid-svg-icons';

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [registerSuccess, setRegisterSuccess] = useState('');
  const { login, register, error, currentUser } = useAuth();
  const navigate = useNavigate();

  // Redirect to dashboard if already logged in
  useEffect(() => {
    if (currentUser) {
      navigate('/dashboard');
    }
  }, [currentUser, navigate]);

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
      const success = await login(formData.email, formData.password);
      if (success) {
        navigate('/dashboard');
      }
    } else {
      // Handle registration
      const success = await register(
        formData.email, 
        formData.password
      );
      
      if (success) {
        setRegisterSuccess('Registration successful! You can now login.');
        // Reset form
        setFormData({
          email: '',
          password: ''
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
                <FontAwesomeIcon icon={faEnvelope} className="input-icon" />
                <label htmlFor="login-email">Email</label>
                <input 
                  type="email" 
                  id="login-email" 
                  name="email" 
                  value={formData.email}
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
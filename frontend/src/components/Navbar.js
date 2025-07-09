import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Navbar.css';

function Navbar() {
  const { isAuthenticated, signOut, user } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await signOut();
    navigate('/');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          AI GitHub
        </Link>
        
        <div className="navbar-links">
          {isAuthenticated ? (
            <>
              <span className="nav-user-email">{user?.attributes?.email}</span>
              <button onClick={handleSignOut} className="nav-button">Sign Out</button>
            </>
          ) : (
            <>
              <Link to="/signin" className="nav-link">Sign In</Link>
              <Link to="/signup" className="nav-link-button">Sign Up</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
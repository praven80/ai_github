import React, { createContext, useState, useEffect, useContext } from 'react';
import { Auth } from 'aws-amplify';

const AuthContext = createContext({
  isAuthenticated: false,
  user: null,
  isLoading: true,
  signIn: () => {},
  signUp: () => {},
  confirmSignUp: () => {},
  signOut: () => {},
  forgotPassword: () => {},
  forgotPasswordSubmit: () => {},
});

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuthState();
  }, []);

  async function checkAuthState() {
    try {
      const session = await Auth.currentSession();
      const user = await Auth.currentAuthenticatedUser();
      setUser(user);
      setIsAuthenticated(true);
    } catch (error) {
      setUser(null);
      setIsAuthenticated(false);
    }
    setIsLoading(false);
  }

  async function signIn(email, password) {
    try {
      const user = await Auth.signIn(email, password);
      setUser(user);
      setIsAuthenticated(true);
      return user;
    } catch (error) {
      throw error;
    }
  }

  async function signUp(email, password) {
    try {
        const { user } = await Auth.signUp({
        username: email,
        password,
        attributes: { email },
        });
        return user;
    } catch (error) {
        throw error;
    }
    }

  async function confirmSignUp(email, code) {
    // This is still needed for manual confirmation if auto-confirm fails
    try {
        await Auth.confirmSignUp(email, code);
        return true;
    } catch (error) {
        throw error;
    }
    }

  async function signOut() {
    try {
      await Auth.signOut();
      setUser(null);
      setIsAuthenticated(false);
    } catch (error) {
      console.error('Error signing out:', error);
    }
  }

  async function forgotPassword(email) {
    try {
      await Auth.forgotPassword(email);
      return true;
    } catch (error) {
      throw error;
    }
  }

  async function forgotPasswordSubmit(email, code, newPassword) {
    try {
      await Auth.forgotPasswordSubmit(email, code, newPassword);
      return true;
    } catch (error) {
      throw error;
    }
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        isLoading,
        signIn,
        signUp,
        confirmSignUp,
        signOut,
        forgotPassword,
        forgotPasswordSubmit,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
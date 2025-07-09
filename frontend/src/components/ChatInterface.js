import React, { useState, useEffect, useRef } from 'react';
import { fetchRepoConversation } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import CustomMarkdownRenderer from './CustomMarkdownRenderer';
import './ChatInterface.css';

const UserIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 8.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5zm3.5 1.5h-7a3.5 3.5 0 00-3.5 3.5v.5c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-.5a3.5 3.5 0 00-3.5-3.5z"/>
  </svg>
);

const GitHubIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
  </svg>
);

function ChatInterface({ repoPath, selectedConversation = null }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);
  const { isAuthenticated, user } = useAuth();

  useEffect(() => {
    if (selectedConversation) {
      // Load selected conversation
      console.log("Loading selected conversation:", selectedConversation);
      setConversationId(selectedConversation.conversationId);
      setMessages(selectedConversation.messages || []);
    } else {
      // Add initial welcome message
      setMessages([
        {
          role: 'assistant',
          content: "👋 Hi there! I'm ready to help you with the " + repoPath + " repository. What would you like to know?"
        }
      ]);
      // Generate new conversation ID
      const newId = "conv_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
      console.log("Generated new conversation ID:", newId);
      setConversationId(newId);
    }
  }, [repoPath, selectedConversation]);

  useEffect(() => {
    // Scroll to bottom whenever messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!input.trim()) return;
    
    const userMessage = input;
    setInput('');
    
    // Add user message to chat
    const updatedMessages = [...messages, { role: 'user', content: userMessage }];
    setMessages(updatedMessages);
    
    // Set loading state
    setIsLoading(true);
    
    try {
      console.log('Sending message to API:', userMessage, 'for repo:', repoPath);
      // Send message to API with conversation ID
      const response = await fetchRepoConversation(repoPath, userMessage, conversationId);
      console.log('API response received:', response);
      
      // Create final messages array with bot response
      const finalMessages = [
        ...updatedMessages,
        { role: 'assistant', content: response.answer }
      ];
      
      // Update state with all messages
      setMessages(finalMessages);
      
      // Update conversation ID if a new one was assigned
      if (response.conversationId && response.conversationId !== conversationId) {
        console.log(`Updating conversation ID from ${conversationId} to ${response.conversationId}`);
        setConversationId(response.conversationId);
      }
      
    } catch (error) {
      console.error('Error fetching conversation:', error);
      const errorContent = "Sorry, I encountered an error: " + error.message + ". Please try again.";
      setMessages(prev => [
        ...prev, 
        { role: 'assistant', content: errorContent }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-icon">
              {message.role === 'user' ? <UserIcon /> : <GitHubIcon />}
            </div>
            <div className="message-content">
              <CustomMarkdownRenderer content={message.content} />
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <div className="message-icon">
              <GitHubIcon />
            </div>
            <div className="message-content loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <form className="chat-input-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this repository..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
      
      {isAuthenticated && (
        <div style={{fontSize: '0.8em', color: '#666', padding: '5px 10px'}}>
          <span>Conversation ID: {conversationId}</span>
          {user && <span style={{marginLeft: '10px'}}>User: {user.attributes?.email || user.username}</span>}
        </div>
      )}
    </div>
  );
}

export default ChatInterface;
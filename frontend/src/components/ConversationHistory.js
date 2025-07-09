import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { fetchConversationHistory } from '../services/api';
import './ConversationHistory.css';

function formatDate(timestamp) {
  if (!timestamp) return 'Unknown date';
  try {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric'
    }).format(date);
  } catch (error) {
    console.error("Date format error:", error);
    return 'Invalid date';
  }
}

function ConversationHistory({ onSelectConversation, currentRepoPath }) {
  const [conversations, setConversations] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { isAuthenticated, user } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      setConversations({});
      setLoading(false);
      return;
    }

    async function loadConversationHistory() {
      try {
        setLoading(true);
        console.log("Fetching conversation history...");
        
        // Get history with error handling
        const history = await fetchConversationHistory();
        
        // If empty, don't show error
        if (!history || history.length === 0) {
          console.log("No conversation history found or endpoint not available");
          setConversations({});
          setLoading(false);
          return;
        }
        
        // Group conversations by repository
        const groupedByRepo = history.reduce((acc, conv) => {
          const repo = conv.repoPath || 'unknown-repo';
          if (!acc[repo]) {
            acc[repo] = [];
          }
          acc[repo].push(conv);
          return acc;
        }, {});
        
        console.log("Grouped conversations:", Object.keys(groupedByRepo));
        setConversations(groupedByRepo);
        setError('');
      } catch (err) {
        console.error('Error fetching conversation history:', err);
        // Don't show error to user, just log it
        setConversations({});
      } finally {
        setLoading(false);
      }
    }

    loadConversationHistory();
  }, [isAuthenticated, user]);

  if (loading) {
    return <div className="conversation-history loading">Loading conversations...</div>;
  }

  // Only show error if explicitly set
  if (error) {
    return <div className="conversation-history error">{error}</div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="conversation-history not-authenticated">
        <p>Sign in to view your conversation history</p>
      </div>
    );
  }

  // Get all repos
  const repos = Object.keys(conversations);
  
  // If no conversations
  if (repos.length === 0) {
    return (
      <div className="conversation-history empty">
        <p>No conversation history yet</p>
        <p className="history-hint">Your conversations will appear here after you chat</p>
      </div>
    );
  }

  return (
    <div className="conversation-history">
      <h3>Conversation History</h3>
      
      {/* Current repo conversations */}
      {conversations[currentRepoPath] && (
        <div className="repo-conversations current-repo">
          <h4>Current Repository</h4>
          <ul>
            {conversations[currentRepoPath].map((conv, idx) => (
              <li key={conv.conversationId || idx} onClick={() => onSelectConversation(conv)}>
                <div className="conversation-item">
                  <div className="conversation-title">{conv.title || 'Conversation'}</div>
                  <div className="conversation-timestamp">{formatDate(conv.timestamp)}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Other repos conversations */}
      <div className="other-repos">
        <h4>Other Repositories</h4>
        {repos
          .filter(repo => repo !== currentRepoPath)
          .map(repo => (
            <div key={repo} className="repo-conversations">
              <h5>{repo}</h5>
              <ul>
                {conversations[repo].map((conv, idx) => (
                  <li key={conv.conversationId || idx} onClick={() => onSelectConversation(conv)}>
                    <div className="conversation-item">
                      <div className="conversation-title">{conv.title || 'Conversation'}</div>
                      <div className="conversation-timestamp">{formatDate(conv.timestamp)}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
      </div>
    </div>
  );
}

export default ConversationHistory;
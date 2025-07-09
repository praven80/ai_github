import React from 'react';
import { useParams } from 'react-router-dom';
import RepoInfo from '../components/RepoInfo';
import ChatInterface from '../components/ChatInterface';
import './RepoChat.css';

function RepoChat() {
  const { owner, repo } = useParams();
  const repoPath = `${owner}/${repo}`;
  
  return (
    <div className="repo-chat-page">
      <div className="repo-chat-container">
        <div className="sidebar-panel">
          <RepoInfo repoPath={repoPath} />
          {/* Conversation history removed */}
        </div>
        <div className="chat-panel">
          <ChatInterface repoPath={repoPath} />
        </div>
      </div>
    </div>
  );
}

export default RepoChat;
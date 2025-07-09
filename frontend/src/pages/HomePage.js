import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './HomePage.css';

function HomePage() {
  const [repoUrl, setRepoUrl] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Extract repo path from URL or use as is
    let repoPath = repoUrl;
    
    // Handle full GitHub URLs
    if (repoUrl.includes('github.com/')) {
      const url = new URL(repoUrl.includes('http') ? repoUrl : `https://${repoUrl}`);
      const pathSegments = url.pathname.split('/').filter(Boolean);
      if (pathSegments.length >= 2) {
        repoPath = `${pathSegments[0]}/${pathSegments[1]}`;
      }
    }
    
    // Navigate to repo chat page
    navigate(`/${repoPath}`);
  };

  return (
    <div className="home-page">
      <div className="hero">
        <h1>AI GitHub: Chat with any Repository</h1>
        <p>Ask questions about code, features, issues, or documentation using natural language</p>
        
        <form onSubmit={handleSubmit} className="repo-form">
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="Enter a GitHub repo (e.g., aws-samples/sample-devgenius-aws-solution-builder)"
            required
          />
          <button type="submit">Start Conversation</button>
        </form>
        
        <div className="examples">
          <p>Or try one of these examples:</p>
          <div className="example-links">
            <button onClick={() => navigate('/aws-samples/sample-devgenius-aws-solution-builder')}>aws-samples/sample-devgenius-aws-solution-builder</button>
            <button onClick={() => navigate('/strands-agents/sdk-python')}>strands-agents/sdk-python</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomePage;

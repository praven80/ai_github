import React, { useState, useEffect } from 'react';
import { fetchRepoInfo } from '../services/api';
import './RepoInfo.css';

function RepoInfo({ repoPath }) {
  const [repoInfo, setRepoInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadRepoInfo = async () => {
      try {
        setLoading(true);
        const info = await fetchRepoInfo(repoPath);
        setRepoInfo(info);
        setError(null);
      } catch (err) {
        console.error('Error fetching repo info:', err);
        setError('Could not load repository information');
      } finally {
        setLoading(false);
      }
    };

    loadRepoInfo();
  }, [repoPath]);

  if (loading) {
    return <div className="repo-info loading">Loading repository information...</div>;
  }

  if (error) {
    return <div className="repo-info error">{error}</div>;
  }

  return (
    <div className="repo-info">
      <h1>{repoInfo.name}</h1>
      <p className="description">{repoInfo.description}</p>
      <div className="repo-stats">
        <div className="stat">
          <span className="label">Stars</span>
          <span className="value">{repoInfo.stars}</span>
        </div>
        <div className="stat">
          <span className="label">Forks</span>
          <span className="value">{repoInfo.forks}</span>
        </div>
        <div className="stat">
          <span className="label">Issues</span>
          <span className="value">{repoInfo.issues}</span>
        </div>
      </div>
      
      <div className="repo-link">
        <a 
          href={`https://github.com/${repoPath}`} 
          target="_blank" 
          rel="noopener noreferrer"
        >
          View on GitHub
        </a>
      </div>
    </div>
  );
}

export default RepoInfo;
import React from 'react';
import ReactMarkdown from 'react-markdown';
import './CustomMarkdownRenderer.css';

const processMarkdownContent = (content) => {
  if (!content) return '';

  // Process the content to fix line break issues
  const sections = content.split(/\n{2,}/g);
  
  const processedSections = sections.map(section => {
    // Preserve list structures
    if (/^(\s*[-*]|\s*\d+\.)/.test(section)) {
      return section.split('\n').join('\n');
    }
    return section;
  });
  
  return processedSections.join('\n\n');
};

const CustomMarkdownRenderer = ({ content }) => {
  // Pre-process the markdown content to handle line breaks
  const processedContent = processMarkdownContent(content);
  
  // Components to customize markdown rendering
  const components = {
    // Add specific styling for headings
    h1: ({ node, ...props }) => <h1 className="md-heading" {...props} />,
    h2: ({ node, ...props }) => <h2 className="md-heading" {...props} />,
    h3: ({ node, ...props }) => <h3 className="md-heading" {...props} />,
    
    // Tighten up lists
    ul: ({ node, ...props }) => <ul className="md-list" {...props} />,
    ol: ({ node, ...props }) => <ol className="md-list" {...props} />,
    li: ({ node, ...props }) => <li className="md-list-item" {...props} />,
    
    // Adjust paragraph spacing
    p: ({ node, ...props }) => <p className="md-paragraph" {...props} />
  };
  
  return (
    <div className="custom-markdown">
      <ReactMarkdown components={components}>
        {processedContent}
      </ReactMarkdown>
    </div>
  );
};

export default CustomMarkdownRenderer;
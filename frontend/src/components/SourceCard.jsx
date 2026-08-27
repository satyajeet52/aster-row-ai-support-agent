import React from 'react';

// Renders an individual knowledge-base citation badge or card,
// displaying the authoritative source filename and relevant heading.
export default function SourceCard({ source }) {
  if (!source || !source.filename) return null;

  return (
    <div className="source-card">
      <div className="source-card-main">
        <span className="source-filename">{source.filename}</span>
        {source.heading && (
          <span className="source-heading">{source.heading}</span>
        )}
      </div>
    </div>
  );
}

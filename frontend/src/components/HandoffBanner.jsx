import React from 'react';

// Displays an alert banner when the agent determines that a human support
// specialist should handle the request (e.g. policy conflicts, order exceptions,
// or actions requiring manual authorization).
export default function HandoffBanner({ message }) {
  return (
    <div className="handoff-banner">
      <div className="handoff-icon-wrapper">
        <span className="handoff-icon">👥</span>
      </div>
      <div className="handoff-content">
        <h4 className="handoff-title">Human Support Recommended</h4>
        <p className="handoff-description">
          {message || 'This issue requires assistance from a support specialist.'}
        </p>
      </div>
    </div>
  );
}

import React from "react";
import ReactMarkdown from "react-markdown";
import SourceCard from "./SourceCard";
import OrderCard from "./OrderCard";
import HandoffBanner from "./HandoffBanner";

// SVG Icons for avatars
const LeafIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.5 10-10 10Z"/>
    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
  </svg>
);

// Renders an individual chat message bubble for either the user or the assistant,
// including markdown formatting, citation cards, order details, and handoff alerts.
export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const isAbstention = !isUser && message.content && (
    message.content.toLowerCase().includes("don't have enough information") ||
    message.content.toLowerCase().includes("do not have enough information") ||
    message.content.toLowerCase().includes("insufficient information") ||
    message.content.toLowerCase().includes("information is insufficient")
  );

  return (
    <div className={`message-row ${isUser ? "message-row-user" : "message-row-assistant"}`}>
      <div className="message-inner">
        <div className="message-avatar">
          {isUser ? "U" : <LeafIcon />}
        </div>

        <div className="message-content-container">
          <div className="message-header">
            <span className="message-sender">{isUser ? "You" : "Aster & Row"}</span>
            {isAbstention && <span className="abstention-tag">Policy Notice</span>}
          </div>

          <div className={`message-bubble ${isAbstention ? "message-bubble-abstention" : ""}`}>
            {isUser ? (
              <p className="user-message-text">{message.content}</p>
            ) : (
              <div className="markdown-body">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>

          {/* Display order lookup result card if present */}
          {message.tool_results && message.tool_results.length > 0 && (
            <div className="message-tool-results">
              {message.tool_results.map((result, idx) => (
                <OrderCard key={idx} orderResult={result} />
              ))}
            </div>
          )}

          {/* Display citations if present */}
          {message.sources && message.sources.length > 0 && (
            <div className="message-sources-section">
              <div className="sources-header-row">
                <span className="sources-icon">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                </span>
                <span className="sources-label">Sources</span>
              </div>
              <div className="sources-list">
                {message.sources.map((src, idx) => (
                  <SourceCard key={idx} source={src} />
                ))}
              </div>
            </div>
          )}

          {/* Display human handoff banner if recommended */}
          {message.handoff_recommended && <HandoffBanner />}
        </div>
      </div>
    </div>
  );
}

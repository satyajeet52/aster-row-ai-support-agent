import React, { useState, useEffect, useRef } from "react";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";

// Generates a short title from the first user message
function generateTitle(messages) {
  const first = messages.find((m) => m.role === "user");
  if (!first) return "New Chat";
  const t = first.content.trim();
  return t.length > 42 ? t.slice(0, 42) + "..." : t;
}

// Groups conversations by date bucket
function groupByDate(conversations) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(today.getDate() - 7);

  const groups = { Today: [], Yesterday: [], "Previous 7 Days": [], Older: [] };
  conversations.forEach((c) => {
    const d = new Date(c.createdAt);
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    if (day >= today) groups.Today.push(c);
    else if (day >= yesterday) groups.Yesterday.push(c);
    else if (day >= weekAgo) groups["Previous 7 Days"].push(c);
    else groups.Older.push(c);
  });
  return groups;
}

// SVG Icons
const LeafIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.5 10-10 10Z"/>
    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
  </svg>
);

const PenIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
  </svg>
);

const ChatIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
);

const TrashIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
);

const MenuIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
);

const CloseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const SunIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1" x2="12" y2="3"/>
    <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/>
    <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
  </svg>
);

const MoonIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
);

export default function App() {
  const [conversations, setConversations] = useState(() => {
    try {
      const saved = localStorage.getItem("aster_conversations");
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [activeId, setActiveId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("aster_theme") || "dark";
    } catch {
      return "dark";
    }
  });

  const messagesEndRef = useRef(null);

  // Synchronize theme with document element and localStorage
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("aster_theme", theme);
    } catch {}
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  // Persist conversations to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("aster_conversations", JSON.stringify(conversations));
    } catch {}
  }, [conversations]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => { scrollToBottom(); }, [messages, isLoading]);

  // Start a brand new session (new chat)
  const startNewSession = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch("/api/new-session", { method: "POST" });
      if (!res.ok) throw new Error("Failed to create session");
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages([]);
      setActiveId(null);
    } catch (err) {
      console.error(err);
      setErrorMessage("Could not connect to backend. Make sure FastAPI is running on port 8000.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { startNewSession(); }, []);

  // Save current messages into the conversations history
  const saveConversation = (id, msgs, sid) => {
    if (!msgs || msgs.length === 0) return;
    const title = generateTitle(msgs);
    setConversations((prev) => {
      const existing = prev.find((c) => c.id === id);
      if (existing) {
        return prev.map((c) => c.id === id ? { ...c, messages: msgs, title, sessionId: sid } : c);
      } else {
        return [{ id, title, messages: msgs, sessionId: sid, createdAt: new Date().toISOString() }, ...prev];
      }
    });
  };

  // Handle sending a message
  const handleSendMessage = async (text) => {
    if (!text.trim() || isLoading) return;
    setErrorMessage(null);

    const userMsg = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setIsLoading(true);

    // Generate a conversation id if none exists
    const convId = activeId || `conv_${Date.now()}`;
    if (!activeId) setActiveId(convId);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      const data = await res.json();

      const assistantMsg = {
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        tool_calls: data.tool_calls || [],
        tool_results: data.tool_results || [],
        handoff_recommended: data.handoff_recommended || false,
      };

      const finalMessages = [...updatedMessages, assistantMsg];
      setMessages(finalMessages);
      saveConversation(convId, finalMessages, sessionId);
    } catch (err) {
      console.error(err);
      setErrorMessage("Error communicating with agent. Please check server status.");
    } finally {
      setIsLoading(false);
    }
  };

  // Load an existing conversation from history
  const loadConversation = async (conv) => {
    if (activeId === conv.id) return;
    setMessages(conv.messages || []);
    setActiveId(conv.id);
    setErrorMessage(null);
    if (conv.sessionId) {
      setSessionId(conv.sessionId);
    } else {
      try {
        const res = await fetch("/api/new-session", { method: "POST" });
        if (res.ok) {
          const data = await res.json();
          setSessionId(data.session_id);
        }
      } catch {}
    }
  };

  // Delete a conversation from history
  const deleteConversation = (e, id) => {
    e.stopPropagation();
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) {
      setMessages([]);
      setActiveId(null);
    }
  };

  const handleSelectPrompt = (text) => handleSendMessage(text);

  const grouped = groupByDate(conversations);
  const currentTitle = activeId
    ? (conversations.find((c) => c.id === activeId)?.title || "New Chat")
    : "New Chat";

  return (
    <div className="app-layout" data-theme={theme}>
      {/* SIDEBAR */}
      <aside className={`sidebar ${sidebarOpen ? "" : "sidebar-collapsed"}`} style={sidebarOpen ? {} : { display: "none" }}>
        <div className="sidebar-header">
          <button className="sidebar-logo-btn" onClick={startNewSession} title="New chat">
            <span className="sidebar-logo-icon" style={{ color: "var(--accent)" }}><LeafIcon /></span>
            <span>Aster &amp; Row</span>
          </button>
          <button className="sidebar-icon-btn" onClick={() => setSidebarOpen(false)} title="Close sidebar">
            <CloseIcon />
          </button>
        </div>

        <button className="sidebar-new-chat-btn" onClick={startNewSession} disabled={isLoading}>
          <PenIcon />
          <span>New chat</span>
        </button>

        {/* Chat History */}
        <div className="sidebar-history">
          {conversations.length === 0 ? (
            <div className="history-empty">No conversations yet.<br/>Start chatting to see history here.</div>
          ) : (
            Object.entries(grouped).map(([label, items]) =>
              items.length > 0 ? (
                <div key={label}>
                  <div className="history-group-label">{label}</div>
                  {items.map((conv) => (
                    <div
                      key={conv.id}
                      className={`history-item ${activeId === conv.id ? "active" : ""}`}
                      onClick={() => loadConversation(conv)}
                      title={conv.title}
                    >
                      <span className="history-item-icon"><ChatIcon /></span>
                      <span className="history-item-title">{conv.title}</span>
                      <div className="history-item-actions">
                        <button
                          className="history-action-btn"
                          onClick={(e) => deleteConversation(e, conv.id)}
                          title="Delete conversation"
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null
            )
          )}
        </div>

        <div className="sidebar-footer">
          <button
            className="sidebar-footer-btn"
            onClick={toggleTheme}
            title={`Switch to ${theme === "dark" ? "Light" : "Dark"} mode`}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
          </button>
        </div>
      </aside>

      {/* MAIN AREA */}
      <div className="main-area">
        {/* Top bar */}
        <div className="main-topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {!sidebarOpen && (
              <button className="topbar-icon-btn" onClick={() => setSidebarOpen(true)} title="Open sidebar">
                <MenuIcon />
              </button>
            )}
            <span className="main-topbar-title">{currentTitle}</span>
          </div>
          <div className="topbar-actions">
            <button
              className="topbar-icon-btn"
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "Light" : "Dark"} mode`}
            >
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            </button>
            <div className="status-badge">
              <span className="status-dot" />
              AI Online
            </div>
            <button
              className="topbar-icon-btn"
              onClick={startNewSession}
              disabled={isLoading}
              title="New chat"
            >
              <PenIcon />
            </button>
          </div>
        </div>

        {/* Chat Canvas */}
        <div className="chat-canvas">
          {errorMessage && (
            <div className="error-banner">{errorMessage}</div>
          )}

          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-logo"><LeafIcon /></div>
              <h1 className="empty-state-title">How can we help you today?</h1>
              <p className="empty-state-desc">
                Ask about return policy, shipping, product care, or track your order in real time.
              </p>
              <div className="example-prompts-grid">
                <button className="example-prompt-card" onClick={() => handleSelectPrompt("How long do I have to return an item?")}>
                  <span className="prompt-icon prompt-icon-box">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                  </span>
                  <div className="prompt-text">
                    <strong>Return Policy</strong>
                    <span>Standard 30-day window &amp; requirements</span>
                  </div>
                </button>
                <button className="example-prompt-card" onClick={() => handleSelectPrompt("Where is ORD-1007 and when will it arrive?")}>
                  <span className="prompt-icon prompt-icon-search">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  </span>
                  <div className="prompt-text">
                    <strong>Track an Order</strong>
                    <span>Check status of ORD-1007</span>
                  </div>
                </button>
                <button className="example-prompt-card" onClick={() => handleSelectPrompt("Do you ship internationally to Canada?")}>
                  <span className="prompt-icon prompt-icon-globe">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                  </span>
                  <div className="prompt-text">
                    <strong>International Shipping</strong>
                    <span>Delivery estimates &amp; duty details</span>
                  </div>
                </button>
                <button className="example-prompt-card" onClick={() => handleSelectPrompt("Can I wash the Breeze Tumbler in the dishwasher?")}>
                  <span className="prompt-icon prompt-icon-shield">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  </span>
                  <div className="prompt-text">
                    <strong>Product Care</strong>
                    <span>Cleaning rules &amp; warranty guidance</span>
                  </div>
                </button>
              </div>
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((msg, index) => (
                <ChatMessage key={index} message={msg} />
              ))}
              {isLoading && (
                <div className="typing-indicator-row">
                  <div className="typing-inner">
                    <div className="typing-avatar" style={{ color: "var(--accent)" }}><LeafIcon /></div>
                    <div className="typing-dots">
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="input-area">
          <div className="input-wrapper">
            <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
          </div>
          <div className="footer-disclaimer">
            Responses are grounded in official Aster &amp; Row policies. Inquiries requiring manual action will be routed to a human specialist.
          </div>
        </div>
      </div>
    </div>
  );
}

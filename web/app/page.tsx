"use client";

import { useEffect, useState, useRef } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  user_name?: string;
  avatar?: string | null;
}

interface Conversation {
  user_id: string;
  user_name: string;
  last_updated: string;
  total_messages: number;
  ai_replies: number;
  last_message: string;
  avatar?: string | null;
  channel_type?: string;
  messages: Message[];
}

interface DashboardState {
  afk_mode: boolean;
  owner_name: string;
  last_sync: string | null;
  bot_connected: boolean;
  stats: {
    total_conversations: number;
    total_messages: number;
    total_ai_replies: number;
  };
  conversations: Conversation[];
}

export default function Dashboard() {
  const [state, setState] = useState<DashboardState | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isToggling, setIsToggling] = useState(false);
  const [mobileView, setMobileView] = useState<"list" | "chat">("list");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Poll state from API every 2.5 seconds
  const fetchState = async () => {
    try {
      const res = await fetch("/api/state", { cache: "no-store" });
      if (res.ok) {
        const data: DashboardState = await res.json();
        setState(data);
        if (!selectedUserId && data.conversations.length > 0) {
          setSelectedUserId(data.conversations[0].user_id);
        }
      }
    } catch (e) {
      console.error("Fetch state error:", e);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 2500);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll chat to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [selectedUserId, state?.conversations]);

  const handleToggleAFK = async () => {
    if (isToggling || !state) return;
    setIsToggling(true);
    try {
      const nextMode = !state.afk_mode;
      const res = await fetch("/api/toggle-afk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ afk_mode: nextMode }),
      });
      if (res.ok) {
        const resData = await res.json();
        setState((prev) => (prev ? { ...prev, afk_mode: resData.afk_mode } : prev));
      }
    } catch (e) {
      console.error("Toggle error:", e);
    } finally {
      setIsToggling(false);
    }
  };

  const selectedConvo = state?.conversations.find((c) => c.user_id === selectedUserId);
  const filteredConversations = (state?.conversations || []).filter((c) =>
    c.user_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.last_message.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatTime = (isoString?: string) => {
    if (!isoString) return "";
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "";
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", backgroundColor: "var(--bg-base)" }}>
      {/* ── Top Navigation Bar ────────────────────────────────────────── */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 24px",
          backgroundColor: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              backgroundColor: "rgba(16, 185, 129, 0.15)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "18px",
            }}
          >
            🤖
          </div>
          <div>
            <h1 style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
              {state?.owner_name || "Sahal"}&apos;s Discord Control
            </h1>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
              <span
                className={state?.bot_connected ? "pulse-dot" : ""}
                style={{
                  width: "7px",
                  height: "7px",
                  borderRadius: "50%",
                  backgroundColor: state?.bot_connected ? "var(--accent-emerald)" : "var(--accent-rose)",
                  display: "inline-block",
                }}
              />
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: "500" }}>
                {state?.bot_connected ? "PC Bot Online" : "PC Bot Offline / Waiting"}
              </span>
            </div>
          </div>
        </div>

        {/* Stats Chips */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              borderRadius: "20px",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              fontSize: "13px",
              color: "var(--text-secondary)",
            }}
          >
            <span>💬</span> Convos: <strong style={{ color: "var(--text-primary)" }}>{state?.stats.total_conversations || 0}</strong>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              borderRadius: "20px",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              fontSize: "13px",
              color: "var(--text-secondary)",
            }}
          >
            <span>📨</span> Received: <strong style={{ color: "var(--text-primary)" }}>{state?.stats.total_messages || 0}</strong>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              borderRadius: "20px",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              fontSize: "13px",
              color: "var(--text-secondary)",
            }}
          >
            <span>🤖</span> Replies: <strong style={{ color: "var(--text-primary)" }}>{state?.stats.total_ai_replies || 0}</strong>
          </div>

          {/* AFK Remote Toggle Switch */}
          <button
            onClick={handleToggleAFK}
            disabled={isToggling}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              borderRadius: "10px",
              backgroundColor: state?.afk_mode ? "var(--accent-emerald)" : "var(--bg-surface-elevated)",
              color: state?.afk_mode ? "#000" : "var(--text-secondary)",
              border: state?.afk_mode ? "1px solid transparent" : "1px solid var(--border-strong)",
              fontWeight: "700",
              fontSize: "13px",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <span>{state?.afk_mode ? "🟢 AFK: ON" : "🔴 AFK: OFF"}</span>
          </button>
        </div>
      </header>

      {/* ── Main App Layout ─────────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left Sidebar: Conversations List */}
        <aside
          style={{
            width: "320px",
            backgroundColor: "var(--bg-surface)",
            borderRight: "1px solid var(--border-subtle)",
            display: "flex",
            flexDirection: "column",
            flexShrink: 0,
          }}
        >
          {/* Search box */}
          <div style={{ padding: "14px" }}>
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: "8px",
                backgroundColor: "var(--bg-base)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontSize: "13px",
                outline: "none",
              }}
            />
          </div>

          {/* List items */}
          <div style={{ flex: 1, overflowY: "auto" }}>
            {filteredConversations.length === 0 ? (
              <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                {state?.bot_connected ? "Waiting for incoming messages..." : "Start the bot on your PC to see messages."}
              </div>
            ) : (
              filteredConversations.map((convo) => {
                const isSelected = convo.user_id === selectedUserId;
                return (
                  <div
                    key={convo.user_id}
                    onClick={() => {
                      setSelectedUserId(convo.user_id);
                      setMobileView("chat");
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "12px 16px",
                      cursor: "pointer",
                      backgroundColor: isSelected ? "var(--bg-surface-elevated)" : "transparent",
                      borderLeft: isSelected ? "3px solid var(--accent-emerald)" : "3px solid transparent",
                      transition: "background-color 0.15s ease",
                    }}
                  >
                    {/* Avatar */}
                    <div
                      style={{
                        width: "42px",
                        height: "42px",
                        borderRadius: "50%",
                        backgroundColor: "var(--bg-base)",
                        border: "1px solid var(--border-subtle)",
                        overflow: "hidden",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        fontWeight: "700",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {convo.avatar ? (
                        <img src={convo.avatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      ) : (
                        convo.user_name.charAt(0).toUpperCase()
                      )}
                    </div>

                    {/* Details */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "3px" }}>
                        <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {convo.user_name}
                        </span>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                          {formatTime(convo.last_updated)}
                        </span>
                      </div>
                      <p style={{ fontSize: "12px", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {convo.last_message}
                      </p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Right Area: Chat History */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", backgroundColor: "var(--bg-base)" }}>
          {selectedConvo ? (
            <>
              {/* Chat Header */}
              <div
                style={{
                  padding: "14px 24px",
                  backgroundColor: "var(--bg-surface)",
                  borderBottom: "1px solid var(--border-subtle)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <div
                    style={{
                      width: "38px",
                      height: "38px",
                      borderRadius: "50%",
                      backgroundColor: "var(--bg-base)",
                      overflow: "hidden",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: "700",
                    }}
                  >
                    {selectedConvo.avatar ? (
                      <img src={selectedConvo.avatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    ) : (
                      selectedConvo.user_name.charAt(0).toUpperCase()
                    )}
                  </div>
                  <div>
                    <h2 style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)" }}>
                      {selectedConvo.user_name}
                    </h2>
                    <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      {selectedConvo.channel_type || "DM"} · {selectedConvo.total_messages} messages ({selectedConvo.ai_replies} bot replies)
                    </span>
                  </div>
                </div>
              </div>

              {/* Message List */}
              <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                {selectedConvo.messages.map((msg, index) => {
                  const isAssistant = msg.role === "assistant";
                  const isGif = msg.content.startsWith("[GIF:");

                  return (
                    <div
                      key={index}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: isAssistant ? "flex-end" : "flex-start",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "11px",
                          color: "var(--text-muted)",
                          marginBottom: "4px",
                          paddingLeft: isAssistant ? "0" : "8px",
                          paddingRight: isAssistant ? "8px" : "0",
                        }}
                      >
                        {isAssistant ? "🤖 Bot" : selectedConvo.user_name} · {formatTime(msg.timestamp)}
                      </div>

                      {isGif ? (
                        <div style={{ maxWidth: "260px", borderRadius: "12px", overflow: "hidden" }}>
                          <img
                            src={msg.content.replace(/\[GIF:[^\]]+\]/, "")}
                            alt="GIF"
                            style={{ width: "100%", borderRadius: "12px", display: "block" }}
                          />
                        </div>
                      ) : (
                        <div
                          style={{
                            maxWidth: "75%",
                            padding: "10px 16px",
                            borderRadius: "16px",
                            borderBottomRightRadius: isAssistant ? "4px" : "16px",
                            borderBottomLeftRadius: isAssistant ? "16px" : "4px",
                            backgroundColor: isAssistant ? "var(--bg-bubble-bot)" : "var(--bg-bubble-user)",
                            color: isAssistant ? "#34d399" : "var(--text-primary)",
                            border: isAssistant ? "1px solid rgba(52, 211, 153, 0.2)" : "1px solid var(--border-subtle)",
                            fontSize: "14px",
                            lineHeight: "1.5",
                            wordBreak: "break-word",
                          }}
                        >
                          {msg.content}
                        </div>
                      )}
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "14px" }}>
              Select a conversation from the left to view messages.
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

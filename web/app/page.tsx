"use client";

import { useEffect, useState, useRef } from "react";

interface UserProfile {
  avatar?: string | null;
  avatar_decoration?: string | null;
  profile_effect?: string | null;
  nameplate?: string | null;
  banner?: string | null;
  status?: string;
  custom_status?: string | null;
  bio?: string | null;
  handle?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  user_name?: string;
  avatar?: string | null;
  avatar_decoration?: string | null;
  attachments?: string[];
  stickers?: string[];
  reactions?: string[];
  is_deleted?: boolean;
  is_edited?: boolean;
  original_content?: string | null;
  reply_to?: { message_id: string; author: string; content: string } | null;
}

interface Conversation {
  user_id: string;
  user_name: string;
  profile?: UserProfile;
  last_updated: string;
  total_messages: number;
  ai_replies: number;
  last_message: string;
  avatar?: string | null;
  channel_type?: string;
  messages: Message[];
  ai_disabled?: boolean;
  chat_mode?: "human" | "ai" | "extreme_ai";
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
  const [showProfileCard, setShowProfileCard] = useState(true);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isTogglingAI, setIsTogglingAI] = useState(false);
  const [isSettingMode, setIsSettingMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleSetMode = async (mode: "human" | "ai" | "extreme_ai") => {
    if (isSettingMode || !selectedUserId || !state) return;
    setIsSettingMode(true);
    try {
      const res = await fetch("/api/set-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: selectedUserId, mode }),
      });
      if (res.ok) {
        const resData = await res.json();
        setState((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            conversations: prev.conversations.map((c) =>
              c.user_id === selectedUserId ? { ...c, chat_mode: resData.chat_mode } : c
            ),
          };
        });
      }
    } catch (e) {
      console.error("Set mode error:", e);
    } finally {
      setIsSettingMode(false);
    }
  };

  const handleToggleAI = async () => {
    if (isTogglingAI || !selectedUserId || !state) return;
    setIsTogglingAI(true);
    try {
      const convo = state.conversations.find((c) => c.user_id === selectedUserId);
      const nextDisabled = convo ? !convo.ai_disabled : true;
      const res = await fetch("/api/toggle-ai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: selectedUserId, ai_disabled: nextDisabled }),
      });
      if (res.ok) {
        const resData = await res.json();
        setState((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            conversations: prev.conversations.map((c) =>
              c.user_id === selectedUserId ? { ...c, ai_disabled: resData.ai_disabled } : c
            ),
          };
        });
      }
    } catch (e) {
      console.error("Toggle AI error:", e);
    } finally {
      setIsTogglingAI(false);
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim() || !selectedUserId || isSending) return;
    setIsSending(true);
    try {
      const res = await fetch("/api/send-message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: selectedUserId, content: inputText.trim() }),
      });
      if (res.ok) {
        setInputText("");
        fetchState();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(`Failed to send message: ${errData.error || "Unknown error"}`);
      }
    } catch (e) {
      console.error("Send message error:", e);
      alert("Failed to send message due to a network error.");
    } finally {
      setIsSending(false);
    }
  };

  // Poll state from API every 2.5 seconds
  const fetchState = async () => {
    try {
      const res = await fetch("/api/state", { cache: "no-store" });
      if (res.ok) {
        const data: DashboardState = await res.json();
        setState(data);
        setSelectedUserId((current) => {
          if (!current && data.conversations.length > 0) {
            return data.conversations[0].user_id;
          }
          return current;
        });
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

  const getStatusColor = (status?: string) => {
    switch (status?.toLowerCase()) {
      case "online":
        return "#22c55e";
      case "idle":
        return "#f59e0b";
      case "dnd":
        return "#ef4444";
      default:
        return "#64748b";
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
              width: "38px",
              height: "38px",
              borderRadius: "12px",
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
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  backgroundColor: state?.bot_connected ? "var(--accent-emerald)" : "var(--accent-rose)",
                  display: "inline-block",
                }}
              />
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: "500" }}>
                {state?.bot_connected ? "Bot Connected · PC Active" : "Waiting for PC Bot..."}
              </span>
            </div>
          </div>
        </div>

        {/* Stats Chips & Toggle */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 14px",
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
              padding: "6px 14px",
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
              padding: "6px 14px",
              borderRadius: "20px",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              fontSize: "13px",
              color: "var(--text-secondary)",
            }}
          >
            <span>🤖</span> Replies: <strong style={{ color: "var(--text-primary)" }}>{state?.stats.total_ai_replies || 0}</strong>
          </div>

          <button
            onClick={handleToggleAFK}
            disabled={isToggling}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 18px",
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

      {/* ── Main Layout ─────────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left Sidebar: Conversations */}
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
          <div style={{ padding: "14px" }}>
            <input
              type="text"
              placeholder="Search chats & members..."
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

          <div style={{ flex: 1, overflowY: "auto" }}>
            {filteredConversations.length === 0 ? (
              <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                {state?.bot_connected ? "Waiting for incoming messages..." : "Start the bot on your PC to see messages."}
              </div>
            ) : (
              filteredConversations.map((convo) => {
                const isSelected = convo.user_id === selectedUserId;
                const profile = convo.profile || {};
                const statusColor = getStatusColor(profile.status);

                return (
                  <div
                    key={convo.user_id}
                    onClick={() => setSelectedUserId(convo.user_id)}
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
                    {/* Avatar with Status & Deco */}
                    <div style={{ position: "relative", width: "42px", height: "42px", flexShrink: 0 }}>
                      <div
                        style={{
                          width: "100%",
                          height: "100%",
                          borderRadius: "50%",
                          backgroundColor: "var(--bg-base)",
                          border: "1px solid var(--border-subtle)",
                          overflow: "hidden",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontWeight: "700",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {profile.avatar ? (
                          <img src={profile.avatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                        ) : (
                          convo.user_name.charAt(0).toUpperCase()
                        )}
                      </div>

                      {/* Avatar Decoration Overlay */}
                      {profile.avatar_decoration && (
                        <img
                          src={profile.avatar_decoration}
                          alt="Deco"
                          style={{
                            position: "absolute",
                            top: "-12%",
                            left: "-12%",
                            width: "124%",
                            height: "124%",
                            pointerEvents: "none",
                          }}
                        />
                      )}

                      {/* Status Dot */}
                      <span
                        style={{
                          position: "absolute",
                          bottom: "0px",
                          right: "0px",
                          width: "10px",
                          height: "10px",
                          borderRadius: "50%",
                          backgroundColor: statusColor,
                          border: "2px solid var(--bg-surface)",
                        }}
                      />
                    </div>

                    {/* Details */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" }}>
                        <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{convo.user_name}</span>
                          {convo.ai_disabled ? (
                            <span style={{ fontSize: "10px", color: "var(--accent-rose)", fontWeight: "700", backgroundColor: "rgba(239, 68, 68, 0.15)", padding: "1px 5px", borderRadius: "4px", flexShrink: 0 }}>PAUSED</span>
                          ) : convo.chat_mode === "extreme_ai" ? (
                            <span style={{ fontSize: "10px", color: "#f59e0b", fontWeight: "700", backgroundColor: "rgba(245, 158, 11, 0.15)", padding: "1px 5px", borderRadius: "4px", flexShrink: 0 }}>🔥 EXTREME</span>
                          ) : convo.chat_mode === "ai" ? (
                            <span style={{ fontSize: "10px", color: "var(--accent-cyan)", fontWeight: "700", backgroundColor: "rgba(56, 189, 248, 0.15)", padding: "1px 5px", borderRadius: "4px", flexShrink: 0 }}>🤖 AI</span>
                          ) : (
                            <span style={{ fontSize: "10px", color: "var(--accent-emerald)", fontWeight: "700", backgroundColor: "rgba(16, 185, 129, 0.15)", padding: "1px 5px", borderRadius: "4px", flexShrink: 0 }}>🧑 HUMAN</span>
                          )}
                        </span>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", flexShrink: 0, marginLeft: "4px" }}>
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

        {/* Center: Chat Stream */}
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
                  <div style={{ position: "relative", width: "40px", height: "40px" }}>
                    <div
                      style={{
                        width: "100%",
                        height: "100%",
                        borderRadius: "50%",
                        backgroundColor: "var(--bg-base)",
                        overflow: "hidden",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontWeight: "700",
                      }}
                    >
                      {selectedConvo.profile?.avatar ? (
                        <img src={selectedConvo.profile.avatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      ) : (
                        selectedConvo.user_name.charAt(0).toUpperCase()
                      )}
                    </div>
                    {selectedConvo.profile?.avatar_decoration && (
                      <img
                        src={selectedConvo.profile.avatar_decoration}
                        alt="Deco"
                        style={{
                          position: "absolute",
                          top: "-12%",
                          left: "-12%",
                          width: "124%",
                          height: "124%",
                          pointerEvents: "none",
                        }}
                      />
                    )}
                  </div>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <h2 style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)" }}>
                        {selectedConvo.user_name}
                      </h2>
                      <span
                        style={{
                          fontSize: "11px",
                          padding: "2px 8px",
                          borderRadius: "12px",
                          backgroundColor: "var(--bg-surface-elevated)",
                          color: getStatusColor(selectedConvo.profile?.status),
                          fontWeight: "600",
                          textTransform: "capitalize",
                        }}
                      >
                        {selectedConvo.profile?.status || "offline"}
                      </span>
                    </div>
                    {selectedConvo.profile?.custom_status && (
                      <div style={{ fontSize: "12px", color: "var(--accent-cyan)", marginTop: "2px" }}>
                        ✨ {selectedConvo.profile.custom_status}
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  {/* 3 Chat Modes Selector */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      backgroundColor: "var(--bg-base)",
                      borderRadius: "10px",
                      padding: "3px",
                      border: "1px solid var(--border-subtle)",
                      gap: "2px",
                    }}
                  >
                    <button
                      onClick={() => handleSetMode("human")}
                      disabled={isSettingMode}
                      title="Human Mode: Sahal's casual lazy style, no emojis, short replies, smart and accurate answers"
                      style={{
                        padding: "5px 10px",
                        borderRadius: "7px",
                        border: "none",
                        backgroundColor: (selectedConvo.chat_mode || "human") === "human" ? "rgba(16, 185, 129, 0.2)" : "transparent",
                        color: (selectedConvo.chat_mode || "human") === "human" ? "var(--accent-emerald)" : "var(--text-muted)",
                        fontWeight: (selectedConvo.chat_mode || "human") === "human" ? "700" : "500",
                        fontSize: "12px",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      🧑 Human
                    </button>
                    <button
                      onClick={() => handleSetMode("ai")}
                      disabled={isSettingMode}
                      title="AI Mode: Friendly bot, moderate emojis, medium-length clear answers"
                      style={{
                        padding: "5px 10px",
                        borderRadius: "7px",
                        border: "none",
                        backgroundColor: selectedConvo.chat_mode === "ai" ? "rgba(56, 189, 248, 0.2)" : "transparent",
                        color: selectedConvo.chat_mode === "ai" ? "var(--accent-cyan)" : "var(--text-muted)",
                        fontWeight: selectedConvo.chat_mode === "ai" ? "700" : "500",
                        fontSize: "12px",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      🤖 AI
                    </button>
                    <button
                      onClick={() => handleSetMode("extreme_ai")}
                      disabled={isSettingMode}
                      title="Extreme AI Mode: Lots of emojis, long thorough explanations, full assistant"
                      style={{
                        padding: "5px 10px",
                        borderRadius: "7px",
                        border: "none",
                        backgroundColor: selectedConvo.chat_mode === "extreme_ai" ? "rgba(245, 158, 11, 0.2)" : "transparent",
                        color: selectedConvo.chat_mode === "extreme_ai" ? "#f59e0b" : "var(--text-muted)",
                        fontWeight: selectedConvo.chat_mode === "extreme_ai" ? "700" : "500",
                        fontSize: "12px",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      🔥 Extreme AI
                    </button>
                  </div>

                  <button
                    onClick={handleToggleAI}
                    disabled={isTogglingAI}
                    style={{
                      padding: "6px 12px",
                      borderRadius: "8px",
                      backgroundColor: selectedConvo.ai_disabled ? "rgba(239, 68, 68, 0.15)" : "var(--bg-surface-elevated)",
                      border: selectedConvo.ai_disabled ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid var(--border-subtle)",
                      color: selectedConvo.ai_disabled ? "var(--accent-rose)" : "var(--text-secondary)",
                      fontSize: "12px",
                      fontWeight: "600",
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {selectedConvo.ai_disabled ? "⏸️ AI Paused" : "▶️ AI Active"}
                  </button>

                  <button
                    onClick={() => setShowProfileCard(!showProfileCard)}
                    style={{
                      padding: "6px 12px",
                      borderRadius: "8px",
                      backgroundColor: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-secondary)",
                      fontSize: "12px",
                      cursor: "pointer",
                    }}
                  >
                    {showProfileCard ? "Hide Profile" : "Show Profile"}
                  </button>
                </div>
              </div>

              {/* Message History */}
              <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                {selectedConvo.messages.map((msg, index) => {
                  const isAssistant = msg.role === "assistant";
                  const isBotGif = msg.content?.startsWith("[GIF:");
                  const isDeleted = msg.is_deleted;
                  const isEdited = msg.is_edited;
                  const trimmed = (msg.content || "").trim();

                  const isMediaUrl = (url: string) => {
                    const l = url.toLowerCase();
                    // Match by file extension (gif, png, jpg, etc.)
                    if (/\.(gif|png|jpg|jpeg|webp|mp4|mov|webm)(\?.*)?$/.test(l)) return true;
                    // Match known GIF/media CDN domains (no extension needed)
                    const gifDomains = [
                      "giphy.com", "klipy.com",
                      "imgur.com", "cdn.discordapp.com", "media.discordapp.net",
                      "i.imgur.com", "media.tenor.com", "media1.tenor.com",
                      "c.tenor.com", "media.giphy.com", "i.giphy.com",
                    ];
                    return gifDomains.some((d) => l.includes(d));
                  };

                  // Tenor short-link pages (e.g. tenor.com/t5rAQpd0GBf.gif) — not direct media
                  const isTenorShortLink = (url: string) => {
                    const l = url.toLowerCase();
                    return (
                      /tenor\.com\/[a-zA-Z0-9]+/.test(l) &&
                      !l.includes("media.tenor.com") &&
                      !l.includes("c.tenor.com") &&
                      !l.includes("media1.tenor.com")
                    );
                  };

                  // A message is a "plain media URL" if it's ONLY a URL pointing to media
                  const isPlainUrl = /^https?:\/\/\S+$/.test(trimmed) && (isMediaUrl(trimmed) || isTenorShortLink(trimmed));

                  const bubbleBase: React.CSSProperties = {
                    maxWidth: "75%",
                    padding: "10px 16px",
                    borderRadius: "16px",
                    borderBottomRightRadius: isAssistant ? "4px" : "16px",
                    borderBottomLeftRadius: isAssistant ? "16px" : "4px",
                    fontSize: "14px",
                    lineHeight: "1.5",
                    wordBreak: "break-word",
                  };

                  return (
                    <div
                      key={index}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: isAssistant ? "flex-end" : "flex-start",
                        opacity: isDeleted ? 0.7 : 1,
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
                        {isAssistant ? "🤖 Sahal's Bot" : (msg.user_name || selectedConvo.user_name)} · {formatTime(msg.timestamp)}
                        {isEdited && <span style={{ fontSize: "10px", opacity: 0.5, marginLeft: "5px" }}>(edited)</span>}
                      </div>

                      {/* Reply context */}
                      {msg.reply_to && (
                        <div style={{
                          maxWidth: "75%",
                          marginBottom: "4px",
                          padding: "5px 10px",
                          borderLeft: "3px solid var(--accent-emerald)",
                          backgroundColor: "rgba(52,211,153,0.06)",
                          borderRadius: "0 6px 6px 0",
                          fontSize: "12px",
                          color: "var(--text-muted)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}>
                          ↩ <strong>{msg.reply_to.author}</strong>: {msg.reply_to.content}
                        </div>
                      )}

                      {/* Deleted message */}
                      {isDeleted ? (
                        <div style={{
                          ...bubbleBase,
                          backgroundColor: "rgba(248,113,113,0.1)",
                          border: "1px solid rgba(248,113,113,0.3)",
                          color: "#f87171",
                          fontStyle: "italic",
                        }}>
                          🗑️ {msg.content || "[Message deleted]"} <span style={{ fontSize: "11px", opacity: 0.6 }}>(deleted)</span>
                        </div>
                      ) : isBotGif ? (() => {
                        const gifSrc = msg.content.replace(/\[GIF:[^\]]+\]/, "");
                        const isTenor = isTenorShortLink(gifSrc);
                        return isTenor ? (
                          <div style={{ maxWidth: "260px", borderRadius: "12px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
                            <iframe
                              src={gifSrc}
                              style={{ width: "260px", height: "200px", border: "none", borderRadius: "12px", display: "block" }}
                              allowFullScreen
                            />
                          </div>
                        ) : (
                          <div style={{ maxWidth: "260px", borderRadius: "12px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
                            <img src={gifSrc} alt="GIF" style={{ width: "100%", borderRadius: "12px", display: "block" }} />
                          </div>
                        );
                      })() : isPlainUrl ? (() => {
                        const isTenor = isTenorShortLink(trimmed);
                        return isTenor ? (
                          <div style={{ maxWidth: "280px", borderRadius: "12px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
                            <iframe
                              src={trimmed}
                              style={{ width: "280px", height: "220px", border: "none", borderRadius: "12px", display: "block" }}
                              allowFullScreen
                            />
                          </div>
                        ) : (
                          <div style={{ maxWidth: "280px", borderRadius: "12px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
                            <img src={trimmed} alt="Media" style={{ width: "100%", borderRadius: "12px", display: "block" }} />
                          </div>
                        );
                      })() : (
                        msg.content && (
                          <div style={{
                            ...bubbleBase,
                            backgroundColor: isAssistant ? "var(--bg-bubble-bot)" : "var(--bg-bubble-user)",
                            color: isAssistant ? "#34d399" : "var(--text-primary)",
                            border: isAssistant ? "1px solid rgba(52, 211, 153, 0.2)" : "1px solid var(--border-subtle)",
                          }}>
                            {msg.content}
                          </div>
                        )
                      )}

                      {/* Attachments */}
                      {!isDeleted && msg.attachments && msg.attachments.length > 0 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px", maxWidth: "280px" }}>
                          {msg.attachments.map((attUrl, aIdx) => (
                            isMediaUrl(attUrl) ? (
                              <img key={aIdx} src={attUrl} alt="Attachment" style={{ width: "100%", borderRadius: "10px", border: "1px solid var(--border-subtle)" }} />
                            ) : (
                              <a key={aIdx} href={attUrl} target="_blank" rel="noreferrer" style={{ color: "var(--accent-emerald)", fontSize: "12px" }}>📎 Attachment</a>
                            )
                          ))}
                        </div>
                      )}

                      {/* Stickers */}
                      {msg.stickers && msg.stickers.length > 0 && (
                        <div style={{ marginTop: "6px", maxWidth: "160px" }}>
                          {msg.stickers.map((stkUrl, sIdx) => (
                            <img key={sIdx} src={stkUrl} alt="Sticker" style={{ width: "100%" }} />
                          ))}
                        </div>
                      )}

                      {/* Reactions */}
                      {msg.reactions && msg.reactions.length > 0 && (
                        <div style={{ display: "flex", gap: "4px", marginTop: "4px", flexWrap: "wrap" }}>
                          {msg.reactions.map((react, rIdx) => (
                            <span key={rIdx} style={{ padding: "2px 8px", borderRadius: "12px", backgroundColor: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", fontSize: "12px" }}>
                              {react}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input Bar */}
              <div
                style={{
                  display: "flex",
                  gap: "10px",
                  padding: "12px 24px",
                  backgroundColor: "var(--bg-surface)",
                  borderTop: "1px solid var(--border-subtle)",
                  flexShrink: 0,
                }}
              >
                <input
                  type="text"
                  placeholder="Type a message manually..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      handleSendMessage();
                    }
                  }}
                  disabled={isSending}
                  style={{
                    flex: 1,
                    padding: "10px 14px",
                    borderRadius: "8px",
                    backgroundColor: "var(--bg-base)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                    fontSize: "13.5px",
                    outline: "none",
                  }}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={isSending || !inputText.trim()}
                  style={{
                    backgroundColor: "var(--accent-emerald)",
                    color: "#000",
                    border: "none",
                    borderRadius: "8px",
                    padding: "0 20px",
                    fontWeight: "700",
                    fontSize: "13.5px",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    opacity: isSending || !inputText.trim() ? 0.6 : 1,
                  }}
                >
                  {isSending ? "Sending..." : "Send"}
                </button>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "14px" }}>
              Select a conversation to monitor messages and profiles.
            </div>
          )}
        </main>

        {/* Right Sidebar: Rich Discord User Profile Card */}
        {selectedConvo && showProfileCard && (
          <aside
            style={{
              width: "280px",
              backgroundColor: "var(--bg-surface)",
              borderLeft: "1px solid var(--border-subtle)",
              display: "flex",
              flexDirection: "column",
              overflowY: "auto",
            }}
          >
            <h3 style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", padding: "16px 20px 0" }}>
              Discord Profile
            </h3>

            {/* ── Banner + Avatar section ─────────────────── */}
            <div style={{ position: "relative", marginTop: "10px" }}>
              {/* Banner */}
              <div
                style={{
                  width: "100%",
                  height: "80px",
                  backgroundColor: selectedConvo.profile?.banner ? "transparent" : "var(--bg-base)",
                  backgroundImage: selectedConvo.profile?.banner ? `url(${selectedConvo.profile.banner})` : undefined,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* Profile Effect overlay on banner */}
                {selectedConvo.profile?.profile_effect && (
                  <img
                    src={selectedConvo.profile.profile_effect}
                    alt="Profile Effect"
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      opacity: 0.85,
                      pointerEvents: "none",
                      mixBlendMode: "screen",
                    }}
                  />
                )}
                {/* Dark gradient at bottom so avatar reads clearly */}
                <div
                  style={{
                    position: "absolute",
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: "40px",
                    background: "linear-gradient(to bottom, transparent, var(--bg-surface))",
                  }}
                />
              </div>

              {/* Avatar — overlapping the banner */}
              <div
                style={{
                  position: "absolute",
                  bottom: "-36px",
                  left: "20px",
                  width: "72px",
                  height: "72px",
                }}
              >
                <div
                  style={{
                    width: "100%",
                    height: "100%",
                    borderRadius: "50%",
                    backgroundColor: "var(--bg-base)",
                    overflow: "hidden",
                    border: "3px solid var(--bg-surface)",
                  }}
                >
                  {selectedConvo.profile?.avatar ? (
                    <img src={selectedConvo.profile.avatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  ) : (
                    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "24px", fontWeight: "700" }}>
                      {selectedConvo.user_name.charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>
                {/* Avatar Decoration */}
                {selectedConvo.profile?.avatar_decoration && (
                  <img
                    src={selectedConvo.profile.avatar_decoration}
                    alt="Deco"
                    style={{
                      position: "absolute",
                      top: "-14%",
                      left: "-14%",
                      width: "128%",
                      height: "128%",
                      pointerEvents: "none",
                    }}
                  />
                )}
                {/* Status dot */}
                <span
                  style={{
                    position: "absolute",
                    bottom: "2px",
                    right: "2px",
                    width: "14px",
                    height: "14px",
                    borderRadius: "50%",
                    backgroundColor: getStatusColor(selectedConvo.profile?.status),
                    border: "2px solid var(--bg-surface)",
                  }}
                />
              </div>
            </div>

            {/* Name + Handle + Nameplate — below the avatar overlap */}
            <div style={{ marginTop: "44px", padding: "0 20px 0" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <div style={{ fontSize: "17px", fontWeight: "800", color: "var(--text-primary)" }}>
                  {selectedConvo.user_name}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  {selectedConvo.profile?.handle || `@${selectedConvo.user_name}`}
                </div>

                {/* Nameplate badge strip */}
                {selectedConvo.profile?.nameplate && (
                  <div style={{ marginTop: "6px" }}>
                    <img
                      src={selectedConvo.profile.nameplate}
                      alt="Nameplate"
                      style={{
                        maxWidth: "100%",
                        height: "auto",
                        maxHeight: "28px",
                        borderRadius: "6px",
                        objectFit: "contain",
                      }}
                      onError={(e) => {
                        // If image fails, show a styled label fallback
                        (e.currentTarget as HTMLImageElement).style.display = "none";
                      }}
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Rest of profile info */}
            <div style={{ padding: "14px 20px", display: "flex", flexDirection: "column", gap: "12px" }}>
              {/* Custom Status */}
              {selectedConvo.profile?.custom_status && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "10px",
                    backgroundColor: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px" }}>Custom Status</div>
                  <div style={{ fontSize: "13px", color: "var(--text-primary)" }}>✨ {selectedConvo.profile.custom_status}</div>
                </div>
              )}

              {/* Profile Effect label (shows CDN link when no image preview) */}
              {selectedConvo.profile?.profile_effect && (
                <div
                  style={{
                    padding: "8px 14px",
                    borderRadius: "10px",
                    backgroundColor: "rgba(168,85,247,0.08)",
                    border: "1px solid rgba(168,85,247,0.25)",
                    fontSize: "12px",
                    color: "var(--text-muted)",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <span>✨</span>
                  <span style={{ color: "#a855f7" }}>Profile Effect active</span>
                </div>
              )}

              {/* Channel & Stats */}
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "10px",
                  backgroundColor: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  fontSize: "12px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Channel Type</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: "600" }}>{selectedConvo.channel_type || "DM"}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Total Messages</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: "600" }}>{selectedConvo.total_messages}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Bot Replies</span>
                  <span style={{ color: "#34d399", fontWeight: "600" }}>{selectedConvo.ai_replies}</span>
                </div>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

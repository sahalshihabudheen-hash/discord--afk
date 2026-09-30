"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface AvatarHistoryEntry {
  avatar?: string | null;
  avatar_decoration?: string | null;
  previous_avatar?: string | null;
  previous_decoration?: string | null;
  timestamp: string;
  label?: string;
}

interface UserCardData {
  user_id: string;
  user_name: string;
  avatar?: string | null;
  avatar_decoration?: string | null;
  handle?: string;
  channel_type?: string;
  total_messages?: number;
  last_updated?: string;
  avatar_history?: AvatarHistoryEntry[];
  previous_avatar?: string | null;
  avatar_switched_at?: string | null;
}

export default function AvatarsPage() {
  const [users, setUsers] = useState<UserCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"all" | "dm" | "group" | "switched">("all");
  const [lightbox, setLightbox] = useState<{ url: string; title: string } | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch("/api/state", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          const convos = data.conversations || [];
          const mappedUsers: UserCardData[] = convos.map((c: any) => {
            const profile = c.profile || {};
            return {
              user_id: c.user_id,
              user_name: c.user_name || "Unknown",
              avatar: c.avatar || profile.avatar,
              avatar_decoration: profile.avatar_decoration,
              handle: profile.handle || c.user_name,
              channel_type: c.channel_type || "DM",
              total_messages: c.total_messages || (c.messages ? c.messages.length : 0),
              last_updated: c.last_updated,
              avatar_history: profile.avatar_history || c.avatar_history || [],
              previous_avatar: profile.previous_avatar || c.previous_avatar,
              avatar_switched_at: profile.avatar_switched_at || c.avatar_switched_at,
            };
          });
          setUsers(mappedUsers);
        }
      } catch (err) {
        console.error("Failed to load avatars:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Filter and search logic
  const filteredUsers = users.filter((u) => {
    const q = searchQuery.toLowerCase().trim();
    const matchesQuery =
      !q ||
      u.user_name.toLowerCase().includes(q) ||
      (u.handle && u.handle.toLowerCase().includes(q));

    if (!matchesQuery) return false;

    if (filterType === "dm") return u.channel_type === "DM";
    if (filterType === "group") return u.channel_type === "Group DM";
    if (filterType === "switched") {
      return (
        (u.previous_avatar && u.previous_avatar !== u.avatar) ||
        (u.avatar_history && u.avatar_history.length > 1)
      );
    }
    return true;
  });

  const totalCapturedAvatars = users.reduce((sum, u) => {
    return sum + (u.avatar_history?.length || (u.avatar ? 1 : 0));
  }, 0);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "var(--bg-base)", color: "var(--text-primary)" }}>
      {/* Top Header */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 40,
          height: "60px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 28px",
          backgroundColor: "rgba(16, 18, 22, 0.85)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <Link
            href="/"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 14px",
              borderRadius: "8px",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-secondary)",
              textDecoration: "none",
              fontSize: "13px",
              fontWeight: 600,
              transition: "all 0.15s ease",
            }}
          >
            ← Back to Chats
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "22px" }}>🖼️</span>
            <div>
              <h1 style={{ fontSize: "16px", fontWeight: 800, margin: 0, letterSpacing: "-0.01em" }}>
                Avatar Gallery & Switch History
              </h1>
              <span style={{ fontSize: "11px", color: "var(--text-tertiary)" }}>
                Track everyone's current profile picture & historical avatars
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              padding: "4px 12px",
              borderRadius: "20px",
              backgroundColor: "rgba(79, 142, 247, 0.12)",
              border: "1px solid rgba(79, 142, 247, 0.25)",
              color: "var(--accent-primary)",
              fontSize: "12px",
              fontWeight: 600,
            }}
          >
            👥 {users.length} Users
          </div>
          <div
            style={{
              padding: "4px 12px",
              borderRadius: "20px",
              backgroundColor: "rgba(167, 139, 250, 0.12)",
              border: "1px solid rgba(167, 139, 250, 0.25)",
              color: "var(--accent-purple)",
              fontSize: "12px",
              fontWeight: 600,
            }}
          >
            📸 {totalCapturedAvatars} Avatars Saved
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ maxWidth: "1400px", margin: "0 auto", padding: "28px" }}>
        {/* Search & Filter Bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "14px",
            marginBottom: "28px",
            padding: "16px 20px",
            backgroundColor: "var(--bg-surface)",
            borderRadius: "14px",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <div style={{ position: "relative", flex: 1, minWidth: "260px" }}>
            <span
              style={{
                position: "absolute",
                left: "14px",
                top: "50%",
                transform: "translateY(-50%)",
                fontSize: "15px",
                color: "var(--text-tertiary)",
              }}
            >
              🔍
            </span>
            <input
              type="text"
              placeholder="Search users by name, username or handle..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 16px 10px 40px",
                borderRadius: "10px",
                backgroundColor: "var(--bg-base)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontSize: "14px",
                outline: "none",
                transition: "border-color 0.15s ease",
              }}
            />
          </div>

          {/* Filter Pills */}
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <span style={{ fontSize: "12px", color: "var(--text-tertiary)", fontWeight: 600 }}>Filter:</span>
            {[
              { id: "all", label: "All Users" },
              { id: "dm", label: "DMs" },
              { id: "group", label: "Group DMs" },
              { id: "switched", label: "🔄 Switched DP" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterType(f.id as any)}
                style={{
                  padding: "7px 14px",
                  borderRadius: "20px",
                  backgroundColor:
                    filterType === f.id ? "rgba(79, 142, 247, 0.2)" : "var(--bg-surface-elevated)",
                  border:
                    filterType === f.id
                      ? "1px solid var(--accent-primary)"
                      : "1px solid var(--border-subtle)",
                  color: filterType === f.id ? "var(--accent-primary)" : "var(--text-secondary)",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Loading State */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "80px 20px", color: "var(--text-tertiary)" }}>
            <div style={{ fontSize: "40px", marginBottom: "12px" }}>⏳</div>
            <div style={{ fontSize: "16px", fontWeight: 600, color: "var(--text-secondary)" }}>
              Loading avatar library...
            </div>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "80px 20px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "16px",
              border: "1px dashed var(--border-subtle)",
              color: "var(--text-tertiary)",
            }}
          >
            <div style={{ fontSize: "48px", marginBottom: "12px" }}>🔍</div>
            <div style={{ fontSize: "17px", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "6px" }}>
              No matching avatars found
            </div>
            <p style={{ fontSize: "13px" }}>Try searching with a different username or clear the search query.</p>
          </div>
        ) : (
          /* User Avatar Cards Grid */
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
              gap: "20px",
            }}
          >
            {filteredUsers.map((u) => {
              const hasSwitched =
                (u.previous_avatar && u.previous_avatar !== u.avatar) ||
                (u.avatar_history && u.avatar_history.length > 1);

              // Deduplicate timeline history entries
              const timeline: { url: string; label: string; isCurrent: boolean; timestamp?: string }[] = [];
              if (u.avatar) {
                timeline.push({ url: u.avatar, label: "Active Now", isCurrent: true, timestamp: u.last_updated });
              }

              const seen = new Set(u.avatar ? [u.avatar.split("?")[0]] : []);
              const hist = [...(u.avatar_history || [])].reverse();
              for (const entry of hist) {
                if (!entry.avatar) continue;
                const clean = entry.avatar.split("?")[0];
                if (seen.has(clean)) continue;
                seen.add(clean);
                timeline.push({
                  url: entry.avatar,
                  label: entry.label || "Previous DP",
                  isCurrent: false,
                  timestamp: entry.timestamp,
                });
              }

              return (
                <div
                  key={u.user_id}
                  style={{
                    backgroundColor: "var(--bg-surface)",
                    borderRadius: "16px",
                    border: "1px solid var(--border-subtle)",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                    boxShadow: "0 4px 20px rgba(0, 0, 0, 0.25)",
                    transition: "transform 0.18s ease, border-color 0.18s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = "translateY(-3px)";
                    e.currentTarget.style.borderColor = "var(--border-strong)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "translateY(0)";
                    e.currentTarget.style.borderColor = "var(--border-subtle)";
                  }}
                >
                  {/* Card Header Profile */}
                  <div
                    style={{
                      padding: "18px",
                      display: "flex",
                      alignItems: "center",
                      gap: "14px",
                      borderBottom: "1px solid var(--border-subtle)",
                      background: "linear-gradient(180deg, rgba(255,255,255,0.02) 0%, transparent 100%)",
                    }}
                  >
                    {/* Big Avatar */}
                    <div
                      onClick={() =>
                        u.avatar && setLightbox({ url: u.avatar, title: `${u.user_name} — Current Avatar` })
                      }
                      style={{
                        position: "relative",
                        width: "56px",
                        height: "56px",
                        borderRadius: "50%",
                        backgroundColor: "var(--bg-surface-elevated)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "22px",
                        fontWeight: 700,
                        flexShrink: 0,
                        cursor: u.avatar ? "pointer" : "default",
                        border: "2px solid rgba(255,255,255,0.08)",
                      }}
                      title="Click to view full size"
                    >
                      {u.avatar ? (
                        <>
                          <img
                            src={u.avatar}
                            alt=""
                            style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                          {u.avatar_decoration && (
                            <img
                              src={u.avatar_decoration}
                              alt=""
                              style={{
                                position: "absolute",
                                top: "-15%",
                                left: "-15%",
                                width: "130%",
                                height: "130%",
                                pointerEvents: "none",
                              }}
                            />
                          )}
                        </>
                      ) : (
                        (u.user_name[0] || "?").toUpperCase()
                      )}
                    </div>

                    {/* User Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "2px" }}>
                        <span
                          style={{
                            fontWeight: 700,
                            fontSize: "15px",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {u.user_name}
                        </span>
                        {hasSwitched && (
                          <span
                            style={{
                              fontSize: "10px",
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: "4px",
                              backgroundColor: "rgba(168, 85, 247, 0.15)",
                              color: "#c084fc",
                              border: "1px solid rgba(168, 85, 247, 0.3)",
                              whiteSpace: "nowrap",
                            }}
                          >
                            Switched
                          </span>
                        )}
                      </div>
                      <div
                        style={{
                          fontSize: "12px",
                          color: "var(--text-tertiary)",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        @{u.handle || u.user_name}
                      </div>
                    </div>

                    {/* DM or Group Badge */}
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 700,
                        padding: "3px 8px",
                        borderRadius: "6px",
                        backgroundColor:
                          u.channel_type === "Group DM"
                            ? "rgba(167, 139, 250, 0.15)"
                            : "rgba(79, 142, 247, 0.15)",
                        color:
                          u.channel_type === "Group DM"
                            ? "var(--accent-purple)"
                            : "var(--accent-primary)",
                        border:
                          u.channel_type === "Group DM"
                            ? "1px solid rgba(167, 139, 250, 0.3)"
                            : "1px solid rgba(79, 142, 247, 0.3)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {u.channel_type === "Group DM" ? "Group DM" : "DM"}
                    </span>
                  </div>

                  {/* Card Meta Stats */}
                  <div
                    style={{
                      padding: "8px 18px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      fontSize: "11px",
                      color: "var(--text-tertiary)",
                      backgroundColor: "rgba(0,0,0,0.15)",
                      borderBottom: "1px solid var(--border-subtle)",
                    }}
                  >
                    <span>💬 {u.total_messages || 0} messages</span>
                    <span>
                      🕒 {u.last_updated ? new Date(u.last_updated).toLocaleDateString() : "Active"}
                    </span>
                    <span>🖼️ {timeline.length} captured</span>
                  </div>

                  {/* Avatar Switch History Section */}
                  <div style={{ padding: "16px 18px 18px", flex: 1, display: "flex", flexDirection: "column" }}>
                    <div
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: "var(--text-tertiary)",
                        marginBottom: "12px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <span>Avatar History Timeline</span>
                      {hasSwitched && (
                        <span style={{ color: "var(--accent-green)", fontSize: "10px", fontWeight: 700 }}>
                          ✓ DP Change Detected
                        </span>
                      )}
                    </div>

                    {/* Timeline items horizontal scroll */}
                    {timeline.length === 0 ? (
                      <div
                        style={{
                          padding: "16px",
                          textAlign: "center",
                          color: "var(--text-tertiary)",
                          fontSize: "12px",
                          fontStyle: "italic",
                        }}
                      >
                        No avatar history recorded yet.
                      </div>
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          gap: "12px",
                          overflowX: "auto",
                          paddingBottom: "6px",
                        }}
                      >
                        {timeline.map((entry, idx) => (
                          <div
                            key={idx}
                            onClick={() =>
                              setLightbox({
                                url: entry.url,
                                title: `${u.user_name} — ${entry.label} (${entry.timestamp ? new Date(entry.timestamp).toLocaleDateString() : ""})`,
                              })
                            }
                            style={{
                              display: "flex",
                              flexDirection: "column",
                              alignItems: "center",
                              gap: "6px",
                              flexShrink: 0,
                              cursor: "pointer",
                            }}
                          >
                            <div
                              style={{
                                width: "48px",
                                height: "48px",
                                borderRadius: "50%",
                                backgroundColor: "var(--bg-surface-elevated)",
                                border: entry.isCurrent
                                  ? "2px solid var(--accent-green)"
                                  : "2px solid var(--border-subtle)",
                                boxShadow: entry.isCurrent ? "0 0 10px rgba(52, 211, 153, 0.4)" : "none",
                                overflow: "hidden",
                                transition: "transform 0.15s ease, border-color 0.15s ease",
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.transform = "scale(1.1)";
                                e.currentTarget.style.borderColor = "var(--accent-primary)";
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.transform = "scale(1)";
                                e.currentTarget.style.borderColor = entry.isCurrent
                                  ? "var(--accent-green)"
                                  : "var(--border-subtle)";
                              }}
                            >
                              <img
                                src={entry.url}
                                alt=""
                                style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }}
                                loading="lazy"
                              />
                            </div>
                            <span
                              style={{
                                fontSize: "10px",
                                fontWeight: entry.isCurrent ? 700 : 500,
                                color: entry.isCurrent ? "var(--accent-green)" : "var(--text-tertiary)",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {entry.label}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* Fullscreen Lightbox Modal */}
      {lightbox && (
        <div
          onClick={() => setLightbox(null)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            backgroundColor: "rgba(0, 0, 0, 0.88)",
            backdropFilter: "blur(12px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            gap: "16px",
            padding: "20px",
            cursor: "pointer",
          }}
        >
          <button
            onClick={() => setLightbox(null)}
            style={{
              position: "absolute",
              top: "24px",
              right: "28px",
              padding: "8px 16px",
              borderRadius: "8px",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
              fontSize: "14px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            ✕ Close
          </button>
          <img
            src={lightbox.url}
            alt="Fullsize Avatar"
            onClick={(e) => e.stopPropagation()}
            style={{
              maxWidth: "min(460px, 90vw)",
              maxHeight: "80vh",
              borderRadius: "20px",
              boxShadow: "0 20px 60px rgba(0,0,0,0.8)",
              border: "2px solid rgba(255,255,255,0.1)",
              cursor: "default",
            }}
          />
          <div
            style={{
              color: "var(--text-secondary)",
              fontSize: "14px",
              fontWeight: 600,
              textAlign: "center",
            }}
          >
            {lightbox.title}
          </div>
        </div>
      )}
    </div>
  );
}

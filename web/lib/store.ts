// In-memory global store for Vercel deployment with rich Discord profile & media support

import fs from "fs";
import path from "path";

const FILE_PATH = path.join(process.cwd(), "conversations.json");

function loadFromFile() {
  try {
    if (fs.existsSync(FILE_PATH)) {
      const data = fs.readFileSync(FILE_PATH, "utf-8");
      return JSON.parse(data);
    }
  } catch (e) {
    console.warn("Unable to read conversations.json:", e);
  }
  return null;
}

export function saveToFile(state: DashboardState) {
  try {
    fs.writeFileSync(FILE_PATH, JSON.stringify(state, null, 2), "utf-8");
  } catch (e) {
    // Ignore error if filesystem is read-only (e.g. Vercel)
  }
}

export interface UserProfile {
  avatar?: string | null;
  avatar_decoration?: string | null;
  banner?: string | null;
  status?: "online" | "idle" | "dnd" | "offline" | string;
  custom_status?: string | null;
  bio?: string | null;
  handle?: string;
}

export interface Message {
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
  deleted_at?: string | null;
  edited_at?: string | null;
}

export interface Conversation {
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
  chat_mode?: "human" | "ai" | "extreme_ai" | "romance";
}

export interface RpcConfig {
  enabled: boolean;
  activity_type: "playing" | "listening" | "watching" | "streaming" | "competing" | "custom" | "none" | string;
  name: string;
  application_id?: string | number;
  details?: string;
  state?: string;
  emoji?: string;
  large_image?: string;
  large_text?: string;
  small_image?: string;
  small_text?: string;
  stream_url?: string;
  status: "online" | "idle" | "dnd" | "invisible" | string;
  show_timestamp: boolean;
  start_time?: number | null;
}

export interface VoiceState {
  in_vc: boolean;
  channel_id?: string | null;
  channel_name?: string | null;
  guild_id?: string | null;
  guild_name?: string | null;
  self_mute?: boolean;
  self_deaf?: boolean;
}

export interface MusicTrack {
  title: string;
  url: string;
  duration?: string;
  thumbnail?: string;
  channel?: string;
}

export interface MusicState {
  is_playing: boolean;
  is_paused: boolean;
  volume: number;
  current_track?: MusicTrack | null;
}

export interface MusicCommand {
  action: "play" | "pause" | "resume" | "stop" | "volume";
  query?: string;
  volume?: number;
}

export interface DashboardState {
  afk_mode: boolean;
  owner_name: string;
  last_sync: string | null;
  bot_connected: boolean;
  rpc_config?: RpcConfig;
  voice_state?: VoiceState;
  music_state?: MusicState;
  stats: {
    total_conversations: number;
    total_messages: number;
    total_ai_replies: number;
  };
  conversations: Conversation[];
}

export interface PendingMessage {
  user_id: string;
  content: string;
}

// Global reference for Node serverless environment
declare global {
  var __GLOBAL_BOT_STATE: DashboardState | undefined;
  var __PENDING_MESSAGES: PendingMessage[] | undefined;
  var __PENDING_RPC: RpcConfig | null | undefined;
  var __PENDING_MUSIC_COMMANDS: MusicCommand[] | undefined;
  var __GROQ_API_KEY: string | undefined;
}

export function setSyncedGroqKey(key?: string) {
  if (key && key !== "your_groq_api_key_here") {
    global.__GROQ_API_KEY = key;
  }
}

export function getSyncedGroqKey(): string | undefined {
  return global.__GROQ_API_KEY;
}

export function getPendingMessages(): PendingMessage[] {
  if (!global.__PENDING_MESSAGES) {
    global.__PENDING_MESSAGES = [];
  }
  return global.__PENDING_MESSAGES;
}

export function addPendingMessage(msg: PendingMessage) {
  const queue = getPendingMessages();
  queue.push(msg);
}

export function clearPendingMessages() {
  global.__PENDING_MESSAGES = [];
}

export function getPendingMusicCommands(): MusicCommand[] {
  if (!global.__PENDING_MUSIC_COMMANDS) {
    global.__PENDING_MUSIC_COMMANDS = [];
  }
  return global.__PENDING_MUSIC_COMMANDS;
}

export function addPendingMusicCommand(cmd: MusicCommand) {
  const queue = getPendingMusicCommands();
  queue.push(cmd);
}

export function clearPendingMusicCommands() {
  global.__PENDING_MUSIC_COMMANDS = [];
}

export function getPendingRpc(): RpcConfig | null | undefined {
  return global.__PENDING_RPC;
}

export function setPendingRpc(rpc: RpcConfig) {
  global.__PENDING_RPC = rpc;
}

export function clearPendingRpc() {
  global.__PENDING_RPC = null;
}

const defaultRpcConfig: RpcConfig = {
  enabled: true,
  activity_type: "playing",
  name: "Writing assignment",
  details: "Chapter 4 Draft",
  state: "Final Polish",
  emoji: "📝",
  stream_url: "",
  status: "dnd",
  show_timestamp: true,
  start_time: null,
};

const defaultState: DashboardState = {
  afk_mode: true,
  owner_name: "Sahal",
  last_sync: null,
  bot_connected: false,
  rpc_config: defaultRpcConfig,
  stats: {
    total_conversations: 0,
    total_messages: 0,
    total_ai_replies: 0,
  },
  conversations: [],
};

export function getGlobalState(): DashboardState {
  if (!global.__GLOBAL_BOT_STATE) {
    const loaded = loadFromFile();
    if (loaded) {
      global.__GLOBAL_BOT_STATE = loaded;
    } else {
      global.__GLOBAL_BOT_STATE = { ...defaultState };
    }
  }

  // Check if bot sent a heartbeat in the last 45 seconds
  if (global.__GLOBAL_BOT_STATE.last_sync) {
    const lastSyncTime = new Date(global.__GLOBAL_BOT_STATE.last_sync).getTime();
    const now = Date.now();
    global.__GLOBAL_BOT_STATE.bot_connected = (now - lastSyncTime) < 45000;
  }

  return global.__GLOBAL_BOT_STATE;
}

export function updateGlobalState(partial: Partial<DashboardState>): DashboardState {
  const current = getGlobalState();
  
  // Merge conversations to preserve the ai_disabled status & chat_mode from local store
  const mergedConversations = (partial.conversations || []).map((convo) => {
    const existing = current.conversations.find((c) => c.user_id === convo.user_id);
    return {
      ...convo,
      ai_disabled: existing ? existing.ai_disabled : (convo.ai_disabled || false),
      chat_mode: (existing?.chat_mode || convo.chat_mode || "human") as "human" | "ai" | "extreme_ai",
    };
  });

  global.__GLOBAL_BOT_STATE = {
    ...current,
    ...partial,
    conversations: mergedConversations,
    last_sync: new Date().toISOString(),
    bot_connected: true,
  };
  saveToFile(global.__GLOBAL_BOT_STATE);
  return global.__GLOBAL_BOT_STATE;
}

export function toggleAFK(newMode?: boolean): boolean {
  const current = getGlobalState();
  const target = newMode !== undefined ? newMode : !current.afk_mode;
  current.afk_mode = target;
  saveToFile(current);
  return target;
}

export function toggleAI(userId: string, disabled?: boolean): boolean {
  const current = getGlobalState();
  const convo = current.conversations.find((c) => c.user_id === userId);
  if (convo) {
    const target = disabled !== undefined ? disabled : !convo.ai_disabled;
    convo.ai_disabled = target;
    saveToFile(current);
    return target;
  }
  return false;
}

export function setChatMode(userId: string, mode: "human" | "ai" | "extreme_ai" | "romance"): string {
  const current = getGlobalState();
  const convo = current.conversations.find((c) => c.user_id === userId);
  if (convo) {
    convo.chat_mode = mode;
    saveToFile(current);
    return mode;
  }
  return "human";
}

export function setRpcConfig(newConfig: Partial<RpcConfig>): RpcConfig {
  const current = getGlobalState();
  current.rpc_config = {
    ...(current.rpc_config || defaultRpcConfig),
    ...newConfig,
  };
  saveToFile(current);
  return current.rpc_config;
}

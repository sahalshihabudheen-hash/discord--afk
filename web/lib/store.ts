// In-memory global store for Vercel deployment with rich Discord profile & media support

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
}

export interface DashboardState {
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

// Global reference for Node serverless environment
declare global {
  var __GLOBAL_BOT_STATE: DashboardState | undefined;
}

const defaultState: DashboardState = {
  afk_mode: true,
  owner_name: "Sahal",
  last_sync: null,
  bot_connected: false,
  stats: {
    total_conversations: 0,
    total_messages: 0,
    total_ai_replies: 0,
  },
  conversations: [],
};

export function getGlobalState(): DashboardState {
  if (!global.__GLOBAL_BOT_STATE) {
    global.__GLOBAL_BOT_STATE = { ...defaultState };
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
  global.__GLOBAL_BOT_STATE = {
    ...current,
    ...partial,
    last_sync: new Date().toISOString(),
    bot_connected: true,
  };
  return global.__GLOBAL_BOT_STATE;
}

export function toggleAFK(newMode?: boolean): boolean {
  const current = getGlobalState();
  const target = newMode !== undefined ? newMode : !current.afk_mode;
  current.afk_mode = target;
  return target;
}

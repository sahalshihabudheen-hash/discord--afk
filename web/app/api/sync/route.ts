import { NextResponse } from "next/server";
import {
  getGlobalState,
  updateGlobalState,
  getPendingMessages,
  clearPendingMessages,
  getPendingRpc,
  clearPendingRpc,
  setSyncedGroqKey,
  getPendingMusicCommands,
  clearPendingMusicCommands,
  getPendingBusyMessage,
  clearPendingBusyMessage,
  isScanChatsRequested,
  clearScanChatsRequested,
} from "@/lib/store";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const data = await req.json();
    if (data.groq_api_key) {
      setSyncedGroqKey(data.groq_api_key);
    }
    const pendingRpc = getPendingRpc();
    if (pendingRpc) {
      clearPendingRpc();
    }

    const pendingBusy = getPendingBusyMessage();
    if (pendingBusy) {
      clearPendingBusyMessage();
    }

    const scanRequested = isScanChatsRequested();
    if (scanRequested) {
      clearScanChatsRequested();
    }
    
    // Update state from local PC bot
    updateGlobalState({
      owner_name: data.owner_name || "Sahal",
      stats: data.stats || {
        total_conversations: 0,
        total_messages: 0,
        total_ai_replies: 0,
      },
      conversations: data.conversations || [],
      voice_state: data.voice_state || undefined,
      music_state: data.music_state || undefined,
      ...(!pendingBusy && data.busy_message ? { busy_message: data.busy_message } : {}),
      ...(!pendingRpc && data.rpc_config ? { rpc_config: data.rpc_config } : {}),
    });

    // Also persist to Supabase in background
    try {
      if (data.conversations && Array.isArray(data.conversations) && data.conversations.length > 0) {
        const dbRecords = data.conversations.map((c: any) => ({
          user_id: String(c.user_id),
          user_name: c.user_name || String(c.user_id),
          channel_id: String(c.channel_id || ""),
          channel_type: c.channel_type || "DM",
          profile: c.profile || {},
          last_updated: c.last_updated || new Date().toISOString(),
          total_messages: c.total_messages || 0,
          ai_replies: c.ai_replies || 0,
          ai_disabled: !!c.ai_disabled,
          chat_mode: c.chat_mode || "human",
          busy_notice_sent: !!c.busy_notice_sent,
          messages: c.messages || [],
        }));
        supabase.from("conversations").upsert(dbRecords, { onConflict: "user_id" }).then(() => {});
      }

      supabase.from("bot_state").upsert([
        { key: "afk_mode", value: getGlobalState().afk_mode },
        { key: "stats", value: data.stats || {} },
        { key: "last_sync", value: new Date().toISOString() },
        { key: "busy_message", value: data.busy_message || getGlobalState().busy_message },
        { key: "rpc_config", value: data.rpc_config || getGlobalState().rpc_config },
      ], { onConflict: "key" }).then(() => {});
    } catch (_) {}

    const currentState = getGlobalState();

    // Fetch pending manual messages
    const pending = [...getPendingMessages()];
    clearPendingMessages();

    // Fetch pending music commands
    const pendingMusic = [...getPendingMusicCommands()];
    clearPendingMusicCommands();

    // Extract conversation IDs where AI is disabled
    const disabledConvoIds = (currentState.conversations || [])
      .filter((c) => c.ai_disabled)
      .map((c) => c.user_id);

    // Extract chat modes for each conversation
    const chatModes: Record<string, string> = {};
    (currentState.conversations || []).forEach((c) => {
      if (c.chat_mode) {
        chatModes[c.user_id] = c.chat_mode;
      }
    });

    // Return the cloud's desired AFK mode, pending RPC config, busy message, music commands & chat modes back to the bot
    return NextResponse.json({
      success: true,
      afk_mode: currentState.afk_mode,
      rpc_config: pendingRpc || null,
      busy_message: pendingBusy || currentState.busy_message || null,
      scan_chats_requested: scanRequested,
      disabled_convo_ids: disabledConvoIds,
      chat_modes: chatModes,
      timestamp: new Date().toISOString(),
      pending_messages: pending,
      pending_music_commands: pendingMusic,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Invalid payload" },
      { status: 400 }
    );
  }
}

export async function GET() {
  const state = getGlobalState();
  return NextResponse.json({
    success: true,
    afk_mode: state.afk_mode,
    bot_connected: state.bot_connected,
    last_sync: state.last_sync,
  });
}

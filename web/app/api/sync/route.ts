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
} from "@/lib/store";

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
      ...(!pendingRpc && data.rpc_config ? { rpc_config: data.rpc_config } : {}),
    });

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

    // Return the cloud's desired AFK mode, pending RPC config, music commands & chat modes back to the bot
    return NextResponse.json({
      success: true,
      afk_mode: currentState.afk_mode,
      rpc_config: pendingRpc || null,
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

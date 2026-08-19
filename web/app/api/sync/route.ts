import { NextResponse } from "next/server";
import { getGlobalState, updateGlobalState, getPendingMessages, clearPendingMessages } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const data = await req.json();
    
    // Update state from local PC bot
    updateGlobalState({
      owner_name: data.owner_name || "Sahal",
      stats: data.stats || {
        total_conversations: 0,
        total_messages: 0,
        total_ai_replies: 0,
      },
      conversations: data.conversations || [],
    });

    const currentState = getGlobalState();

    // Fetch pending manual messages
    const pending = [...getPendingMessages()];
    clearPendingMessages();

    // Extract conversation IDs where AI is disabled
    const disabledConvoIds = (currentState.conversations || [])
      .filter((c) => c.ai_disabled)
      .map((c) => c.user_id);

    // Return the cloud's desired AFK mode back to the bot
    return NextResponse.json({
      success: true,
      afk_mode: currentState.afk_mode,
      disabled_convo_ids: disabledConvoIds,
      timestamp: new Date().toISOString(),
      pending_messages: pending,
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

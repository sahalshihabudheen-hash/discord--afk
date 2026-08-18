import { NextResponse } from "next/server";
import { getGlobalState, updateGlobalState } from "@/lib/store";

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

    // Return the cloud's desired AFK mode back to the bot
    return NextResponse.json({
      success: true,
      afk_mode: currentState.afk_mode,
      timestamp: new Date().toISOString(),
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

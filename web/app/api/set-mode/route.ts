import { NextResponse } from "next/server";
import { setChatMode, getGlobalState } from "@/lib/store";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const { user_id, mode } = await req.json().catch(() => ({}));
    if (!user_id) {
      return NextResponse.json({ success: false, error: "Missing user_id" }, { status: 400 });
    }

    const validModes = ["human", "ai", "extreme_ai", "romance"];
    const targetMode = validModes.includes(mode) ? mode : "human";

    const updatedMode = setChatMode(user_id, targetMode as any);
    const state = getGlobalState();

    // Persist directly to Supabase so /api/state polling immediately sees updated mode
    try {
      await supabase
        .from("conversations")
        .update({ chat_mode: updatedMode })
        .eq("user_id", String(user_id));
    } catch (dbErr) {
      console.error("Failed to update chat_mode in Supabase:", dbErr);
    }

    return NextResponse.json({
      success: true,
      user_id,
      chat_mode: updatedMode,
      bot_connected: state.bot_connected,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Failed to set chat mode" },
      { status: 500 }
    );
  }
}

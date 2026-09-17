import { NextResponse } from "next/server";
import { toggleAI, getGlobalState } from "@/lib/store";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const { user_id, ai_disabled } = await req.json().catch(() => ({}));
    if (!user_id) {
      return NextResponse.json({ success: false, error: "Missing user_id" }, { status: 400 });
    }

    const disabledResult = toggleAI(user_id, ai_disabled);
    const state = getGlobalState();

    // Persist directly to Supabase so /api/state polling immediately sees updated AI pause state
    try {
      await supabase
        .from("conversations")
        .update({ ai_disabled: disabledResult })
        .eq("user_id", String(user_id));
    } catch (dbErr) {
      console.error("Failed to update ai_disabled in Supabase:", dbErr);
    }

    return NextResponse.json({
      success: true,
      user_id,
      ai_disabled: disabledResult,
      bot_connected: state.bot_connected,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Failed to toggle AI replies" },
      { status: 500 }
    );
  }
}

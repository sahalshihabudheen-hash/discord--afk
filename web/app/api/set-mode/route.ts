import { NextResponse } from "next/server";
import { setChatMode, getGlobalState } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const { user_id, mode } = await req.json().catch(() => ({}));
    if (!user_id) {
      return NextResponse.json({ success: false, error: "Missing user_id" }, { status: 400 });
    }

    const validModes = ["human", "ai", "extreme_ai"];
    const targetMode = validModes.includes(mode) ? mode : "human";

    const updatedMode = setChatMode(user_id, targetMode as any);
    const state = getGlobalState();

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

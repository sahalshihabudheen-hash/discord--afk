import { NextResponse } from "next/server";
import { toggleAFK, getGlobalState } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const newMode = toggleAFK(body.afk_mode);
    const state = getGlobalState();

    return NextResponse.json({
      success: true,
      afk_mode: newMode,
      bot_connected: state.bot_connected,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Failed to toggle AFK" },
      { status: 500 }
    );
  }
}

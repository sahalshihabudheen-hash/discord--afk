import { NextResponse } from "next/server";
import { requestScanChats, getGlobalState } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function POST() {
  try {
    requestScanChats();
    const state = getGlobalState();
    return NextResponse.json({
      success: true,
      message: "Chat scan request queued for local bot",
      bot_connected: state.bot_connected,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Internal server error" },
      { status: 500 }
    );
  }
}

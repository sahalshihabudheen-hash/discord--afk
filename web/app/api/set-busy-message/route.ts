import { NextResponse } from "next/server";
import { setPendingBusyMessage, getGlobalState } from "@/lib/store";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const { busy_message } = await req.json().catch(() => ({}));
    if (!busy_message || typeof busy_message !== "string") {
      return NextResponse.json(
        { success: false, error: "Missing or invalid busy_message" },
        { status: 400 }
      );
    }

    const trimmed = busy_message.trim();
    setPendingBusyMessage(trimmed);

    try {
      await supabase.from("bot_state").upsert({ key: "busy_message", value: trimmed }, { onConflict: "key" });
    } catch (_) {}

    return NextResponse.json({
      success: true,
      busy_message: trimmed,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Internal server error" },
      { status: 500 }
    );
  }
}

export async function GET() {
  const state = getGlobalState();
  return NextResponse.json({
    success: true,
    busy_message: state.busy_message || "SAHAL_PRO is busy and working on something",
  });
}

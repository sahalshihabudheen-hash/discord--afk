import { NextResponse } from "next/server";
import { addPendingVoiceMessage } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const { user_id, text } = await req.json();
    if (!user_id || !text) {
      return NextResponse.json({ success: false, error: "Missing user_id or text" }, { status: 400 });
    }

    addPendingVoiceMessage({ user_id, text });

    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error?.message || "Internal error" }, { status: 500 });
  }
}

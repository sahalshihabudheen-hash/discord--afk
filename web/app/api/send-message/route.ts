import { NextResponse } from "next/server";
import { addPendingMessage } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const { user_id, content } = await req.json();
    if (!user_id || !content) {
      return NextResponse.json({ success: false, error: "Missing user_id or content" }, { status: 400 });
    }

    addPendingMessage({ user_id, content });

    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error?.message || "Internal error" }, { status: 500 });
  }
}

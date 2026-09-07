import { NextResponse } from "next/server";
import { setPendingBusyMessage, getGlobalState } from "@/lib/store";

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

    setPendingBusyMessage(busy_message.trim());
    return NextResponse.json({
      success: true,
      busy_message: busy_message.trim(),
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

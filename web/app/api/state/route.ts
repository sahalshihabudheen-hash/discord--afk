import { NextResponse } from "next/server";
import { getGlobalState } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function GET() {
  const state = getGlobalState();
  return NextResponse.json(state);
}

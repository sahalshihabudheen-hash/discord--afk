import { NextResponse } from "next/server";
import { setRpcConfig } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const data = await req.json();
    const updated = setRpcConfig(data);
    return NextResponse.json({ success: true, rpc_config: updated });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Invalid payload" },
      { status: 400 }
    );
  }
}

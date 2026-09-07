import { NextResponse } from "next/server";
import { getGlobalState } from "@/lib/store";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { data: convos, error: convosErr } = await supabase
      .from("conversations")
      .select("*")
      .order("last_updated", { ascending: false });

    if (!convosErr && convos && convos.length > 0) {
      const { data: botStateRows } = await supabase.from("bot_state").select("*");
      const stateMap: Record<string, any> = {};
      if (botStateRows) {
        botStateRows.forEach((row: any) => {
          stateMap[row.key] = row.value;
        });
      }

      const memoryState = getGlobalState();
      const lastSync = stateMap["last_sync"] || memoryState.last_sync;
      let botConnected = false;
      if (lastSync) {
        const diff = Date.now() - new Date(lastSync).getTime();
        botConnected = diff < 45000;
      }

      return NextResponse.json({
        ...memoryState,
        afk_mode: stateMap["afk_mode"] !== undefined ? stateMap["afk_mode"] : memoryState.afk_mode,
        busy_message: stateMap["busy_message"] || memoryState.busy_message,
        rpc_config: stateMap["rpc_config"] || memoryState.rpc_config,
        stats: stateMap["stats"] || memoryState.stats,
        last_sync: lastSync,
        bot_connected: botConnected,
        conversations: convos,
      });
    }
  } catch (e) {
    // Fallback to in-memory store
  }

  const state = getGlobalState();
  return NextResponse.json(state);
}

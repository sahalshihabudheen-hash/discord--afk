import { NextResponse } from "next/server";
import { getGlobalState } from "@/lib/store";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

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

      // Compute last_message and avatar for every conversation
      const formattedConvos = convos.map((c: any) => {
        let lastMsg = c.last_message || "";
        if (!lastMsg && Array.isArray(c.messages) && c.messages.length > 0) {
          const lm = c.messages[c.messages.length - 1];
          if (lm.is_deleted) {
            lastMsg = `🗑️ [Deleted]: ${lm.content || ""}`;
          } else if (lm.attachments && lm.attachments.length > 0) {
            lastMsg = "📷 [Attachment / Media]";
          } else if (lm.stickers && lm.stickers.length > 0) {
            lastMsg = "🎨 [Sticker]";
          } else {
            lastMsg = lm.content || "";
          }
        }
        return {
          ...c,
          last_message: lastMsg,
          avatar: c.avatar || c.profile?.avatar || null,
        };
      });

      // Calculate stats dynamically if bot_state stats has 0
      let stats = stateMap["stats"] || memoryState.stats;
      if (!stats || !stats.total_conversations) {
        const totalMsgs = convos.reduce(
          (sum: number, c: any) => sum + (c.total_messages || (Array.isArray(c.messages) ? c.messages.length : 0)),
          0
        );
        const totalReplies = convos.reduce((sum: number, c: any) => sum + (c.ai_replies || 0), 0);
        stats = {
          total_conversations: convos.length,
          total_messages: totalMsgs,
          total_ai_replies: totalReplies,
        };
      }

      return NextResponse.json({
        ...memoryState,
        _debug: {
          source: "supabase",
          supabaseUrl: (supabase as any).supabaseUrl,
          convosCount: convos.length,
          botStateRowsCount: botStateRows?.length,
        },
        afk_mode: stateMap["afk_mode"] !== undefined ? stateMap["afk_mode"] : memoryState.afk_mode,
        busy_message: stateMap["busy_message"] || memoryState.busy_message,
        rpc_config: stateMap["rpc_config"] || memoryState.rpc_config,
        stats: stats,
        last_sync: lastSync,
        bot_connected: botConnected,
        conversations: formattedConvos,
      });
    } else {
      console.warn("Supabase returned empty or error:", convosErr);
      const memoryState = getGlobalState();
      return NextResponse.json({
        ...memoryState,
        _debug: {
          source: "fallback_empty",
          convosErr: convosErr ? { message: convosErr.message, code: convosErr.code, details: convosErr.details } : null,
          convosLength: convos ? convos.length : null,
        },
      });
    }
  } catch (e: any) {
    console.error("Supabase state fetch error:", e);
    const state = getGlobalState();
    return NextResponse.json({
      ...state,
      _debug: { source: "exception", error: e?.message || String(e) },
    });
  }

  const state = getGlobalState();
  return NextResponse.json(state);
}

import { NextResponse } from "next/server";
import { addPendingMusicCommand, getGlobalState } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const { action, query, volume } = await req.json();

    if (!action) {
      return NextResponse.json(
        { success: false, error: "Missing action" },
        { status: 400 }
      );
    }

    if (action === "play" && !query?.trim()) {
      return NextResponse.json(
        { success: false, error: "Song query or YouTube URL is required" },
        { status: 400 }
      );
    }

    // Queue command for local bot to execute
    addPendingMusicCommand({
      action,
      query: query?.trim(),
      volume: typeof volume === "number" ? volume : undefined,
    });

    // Optimistic UI state update
    const state = getGlobalState();
    if (!state.music_state) {
      state.music_state = {
        is_playing: false,
        is_paused: false,
        volume: 80,
        current_track: null,
      };
    }

    if (action === "pause") {
      state.music_state.is_paused = true;
    } else if (action === "resume") {
      state.music_state.is_paused = false;
    } else if (action === "stop") {
      state.music_state.is_playing = false;
      state.music_state.is_paused = false;
      state.music_state.current_track = null;
    } else if (action === "volume" && typeof volume === "number") {
      state.music_state.volume = volume;
    }

    return NextResponse.json({
      success: true,
      music_state: state.music_state,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Internal server error" },
      { status: 500 }
    );
  }
}

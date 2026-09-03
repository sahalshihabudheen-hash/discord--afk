import { NextResponse } from "next/server";
import { getGlobalState, addPendingMessage, saveToFile, getSyncedGroqKey } from "@/lib/store";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

function getGroqApiKey(): string {
  if (process.env.GROQ_API_KEY && process.env.GROQ_API_KEY !== "your_groq_api_key_here") {
    return process.env.GROQ_API_KEY;
  }
  const syncedKey = getSyncedGroqKey();
  if (syncedKey && syncedKey !== "your_groq_api_key_here") {
    return syncedKey;
  }
  const pathsToTry = [
    path.join(process.cwd(), ".env.local"),
    path.join(process.cwd(), ".env"),
    path.join(process.cwd(), "..", ".env"),
  ];
  for (const p of pathsToTry) {
    try {
      if (fs.existsSync(p)) {
        const text = fs.readFileSync(p, "utf-8");
        const match = text.match(/GROQ_API_KEY\s*=\s*(.+)/);
        if (match) {
          const val = match[1].trim().replace(/^["']|["']$/g, "");
          if (val && val !== "your_groq_api_key_here") return val;
        }
      }
    } catch {}
  }
  return "";
}

function getOwnerName(): string {
  if (process.env.YOUR_NAME) return process.env.YOUR_NAME;
  const pathsToTry = [
    path.join(process.cwd(), ".env.local"),
    path.join(process.cwd(), ".env"),
    path.join(process.cwd(), "..", ".env"),
  ];
  for (const p of pathsToTry) {
    try {
      if (fs.existsSync(p)) {
        const text = fs.readFileSync(p, "utf-8");
        const match = text.match(/YOUR_NAME\s*=\s*(.+)/);
        if (match) {
          return match[1].trim().replace(/^["']|["']$/g, "");
        }
      }
    } catch {}
  }
  return "Sahal";
}

export async function POST(req: Request) {
  try {
    const { user_id, prompt, send = true, chat_mode, user_name } = await req.json();
    if (!user_id || !prompt) {
      return NextResponse.json(
        { success: false, error: "Missing user_id or prompt" },
        { status: 400 }
      );
    }

    const state = getGlobalState();
    const convo = state.conversations?.find((c) => c.user_id === user_id);
    const activeMode = chat_mode || convo?.chat_mode || "human";
    const recipientName = user_name || convo?.user_name || "Friend";
    const ownerName = getOwnerName();
    const groqKey = getGroqApiKey();

    if (!groqKey) {
      return NextResponse.json(
        { success: false, error: "GROQ_API_KEY is not configured in .env or environment" },
        { status: 500 }
      );
    }

    const systemPrompt = `You are ${ownerName}'s AI writing assistant on Discord.
${ownerName} wants to send a message to ${recipientName}.
${ownerName} provided this draft, instruction, or rough idea of what to say:
"${prompt}"

Your task: AI-fy this draft into ${ownerName}'s message to ${recipientName}, strictly matching the conversation mode: '${activeMode}'.

MODE INSTRUCTIONS:
- 'human' mode:
  * Match ${ownerName}'s real casual texting style on Discord:
  * ZERO emojis. ABSOLUTELY NEVER ANY EMOJIS.
  * All lowercase letters only.
  * Chill, relaxed, concise.
  * Say 'am' instead of 'I am' / 'I\\'m'.
  * Say 'nah' for no, 'yh' for yes. Use 'bro' sparingly/naturally.
  * Natural Discord slang, short and unbothered.

- 'ai' mode:
  * Helpful, clear, crisp, polite assistant tone.
  * 1 to 3 relevant emojis (👍, ✨, 🙌).
  * Direct and friendly.

- 'extreme_ai' mode:
  * High-energy, confident, enthusiastic AI assistant.
  * Expressive emojis: 🚀🔥💡⚡✨💪.
  * Knowledgeable, punchy.

- 'romance' mode:
  * Deeply affectionate, romantic charm, effortless rizz.
  * Virtual kisses (*mwah*, *forehead kiss* 😘💋), cute hugs (*holds you close* ❤️).
  * Sweet pet names: babe, cutie, sweetheart, darling, angel.
  * Heart-fluttering, warm, confident.

IMPORTANT:
1. Accurately preserve the core intention/facts ${ownerName} wants to convey.
2. Consider recent messages so it fits smoothly into context.
3. Return ONLY the final raw message text to be sent to ${recipientName}.
4. NO introductory text, NO quotes around it, NO reasoning or thinking tags.`;

    const recentHistory = (convo?.messages || []).slice(-6).map((m) => ({
      role: m.role === "user" ? "user" : "assistant",
      content: m.content || "",
    }));

    const messages = [
      { role: "system", content: systemPrompt },
      ...recentHistory,
      { role: "user", content: `Please AI-fy this draft/intent into our message to send: "${prompt}"` },
    ];

    const modelsToTry = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"];
    let aifiedContent = "";

    for (const model of modelsToTry) {
      try {
        const groqRes = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${groqKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model,
            messages,
            max_tokens: activeMode === "human" ? 150 : 500,
            temperature: 0.75,
          }),
        });

        if (groqRes.ok) {
          const json = await groqRes.json();
          const raw = json.choices?.[0]?.message?.content || "";
          let cleaned = raw.replace(/<think>[\s\S]*?(?:<\/think>|$)/gi, "").replace(/<think>/gi, "").trim();
          if ((cleaned.startsWith('"') && cleaned.endsWith('"')) || (cleaned.startsWith("'") && cleaned.endsWith("'"))) {
            cleaned = cleaned.slice(1, -1).trim();
          }
          if (cleaned) {
            aifiedContent = cleaned;
            break;
          }
        }
      } catch (err) {
        console.warn(`[AI-fy API] Groq attempt with ${model} failed:`, err);
      }
    }

    if (!aifiedContent) {
      aifiedContent = prompt.trim();
    }

    if (send) {
      // Queue message for the Discord bot
      addPendingMessage({ user_id, content: aifiedContent });

      // Add to conversation in store for immediate UI reflection
      if (convo) {
        convo.messages.push({
          role: "assistant",
          content: aifiedContent,
          timestamp: new Date().toISOString(),
        });
        convo.total_messages = (convo.total_messages || 0) + 1;
        convo.ai_replies = (convo.ai_replies || 0) + 1;
        convo.last_message = aifiedContent;
        convo.last_updated = new Date().toISOString();
        saveToFile(state);
      }
    }

    return NextResponse.json({
      success: true,
      aified_content: aifiedContent,
      sent: Boolean(send),
    });
  } catch (error: any) {
    console.error("AI-fy route error:", error);
    return NextResponse.json(
      { success: false, error: error?.message || "Failed to AI-fy message" },
      { status: 500 }
    );
  }
}

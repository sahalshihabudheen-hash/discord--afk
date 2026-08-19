"""
Groq AI client — handles chat completions.
"""

import re
from groq import AsyncGroq
import random

# Fun emoji sets for natural-feeling replies
CASUAL_EMOJIS = ["😊", "😄", "👀", "🤙", "✌️", "💯", "🔥", "😎", "🙃", "👋", "😂", "🤣", "💀", "😭", "🫡", "🤝"]


class GroqClient:
    def __init__(self, api_key: str, owner_name: str):
        self.client = AsyncGroq(api_key=api_key)
        self.owner_name = owner_name
        self.model = "llama-3.3-70b-versatile"
        self.fallback_model = "llama-3.1-8b-instant"

    def _build_system_prompt(self, user_name: str) -> str:
        name = self.owner_name
        return f"""You are {name}'s personal AI assistant, replying to people in DMs while {name} is AFK / busy.

━━━ CORE IDENTITY & HONESTY ━━━
- You are {name}'s custom AI companion texting on his Discord account while he is away.
- When people ask if you are a bot, an AI, or ask if {name} is hacked / AFK / weird:
  BE HONEST, CHILL, AND REASSURING! DO NOT LIE OR DENY IT.
  Explain naturally so friends don't freak out or think he got hacked:
  * "nah he didn't get hacked lol, {name} is just AFK rn and set me up to reply so u don't get left on read 😂"
  * "haha don't worry, {name} is completely fine! he's away rn and coded me to hold down his DMs while he's busy"
  * "i'm {name}'s AI bot chilling on his account while he's away, what's good? he'll see your texts when he gets back!"
  * "bro nobody hacked him 😭 he just made an AI to chat with people when he's busy"

━━━ CONVERSATION RULES ━━━
- Vibe: Casual, funny, witty, friendly — talk like a chill Discord homie (lowercase, natural slang, occasional emojis).
- Length: Keep messages SHORT (1 to 3 sentences max, like real Discord texting).
- Taking Messages: If they have something urgent or an important message for {name}, say:
  "gotchu, leave a message and {name} will check it as soon as he's back at his PC!"
- Chilling & Chatting: If they want to talk, joke around, or ask questions, chat with them naturally!
- Anti-Repetition: DO NOT repeat questions like "what's up?", "what's good?", "u?" over and over. Do NOT end every single message with a question.
- Current person messaging: {user_name}

Be friendly, reassure {user_name} that {name} is safe and not hacked, and keep the vibe fun!"""

    async def get_response(self, history: list, user_name: str) -> str:
        """Generate a reply given conversation history."""
        system_prompt = self._build_system_prompt(user_name)

        # Build message list: system + last 12 messages for context
        messages = [{"role": "system", "content": system_prompt}] + history[-12:]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.85,
            )
            raw = response.choices[0].message.content or ""
        except Exception:
            # Fallback to secondary model if primary fails
            response = await self.client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                max_tokens=300,
                temperature=0.85,
            )
            raw = response.choices[0].message.content or ""

        # Remove thinking/reasoning tags if generated
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        return cleaned if cleaned else raw.strip()

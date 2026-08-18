# 🤖 Sahal's Discord AFK Control Bot

An AI-powered Discord self-bot that auto-replies to your DMs and Group DMs when you're AFK,
using **Groq AI** for natural conversations and a **live web dashboard** to monitor everything.

> ⚠️ **Warning**: Self-bots (using your personal Discord token) violate Discord's Terms of Service and can result in account bans. Use at your own risk.

---

## Features

- 🤖 Auto-replies to **DMs and Group DMs only** (ignores server messages)
- 🧠 Powered by **Groq Llama 3.3 70B** — fast, natural, casual replies
- ✍️ Shows **typing indicator** before replying (feels human)
- 📊 **Live dashboard** at `localhost:5000` — view all conversations in real time
- 🔄 **Toggle AFK mode** on/off from the dashboard without restarting
- 🍞 Toast notifications for every new DM
- 💾 Tracks full conversation history per user

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your `.env` file

Copy the example:
```bash
copy .env.example .env
```

Edit `.env` and fill in:

```env
DISCORD_TOKEN=your_discord_user_token
GROQ_API_KEY=your_groq_api_key
YOUR_NAME=Sahal
AFK_MODE=true
```

#### 🔑 Getting your Discord user token

1. Open Discord in your **browser** at [discord.com/app](https://discord.com/app)
2. Press **F12** to open DevTools
3. Go to the **Application** tab → **Local Storage** → `https://discord.com`
4. Find the key named **`token`** — that's your token

   OR in the **Network** tab, send any message, find a request to `discord.com/api`, and look in the request headers for `authorization`.

#### 🔑 Getting your Groq API key

1. Sign up at [console.groq.com](https://console.groq.com)
2. Go to **API Keys** → **Create API Key**
3. Copy and paste it into `.env`

---

### 3. Run the bot

```bash
python run.py
```

Open **http://localhost:5000** in your browser to see the dashboard.

---

## How it works

```
Someone DMs you on Discord
        │
        ▼
Self-bot receives message (DM or Group DM only)
        │
        ▼
Groq AI generates a casual reply
("hey! sahal is afk rn, you're chatting to his ai 🤖 what's up?")
        │
        ▼
Reply sent back to the person
        │
        ▼
Dashboard updates in real time (you see everything)
```

---

## Dashboard

Open **http://localhost:5000** to:
- View all active conversations with message history
- See stats (total convos, messages received, AI replies)
- Toggle AFK mode on/off live
- Get toast notifications for every new DM

---

## File Structure

```
discord control/
├── run.py                    ← Start here
├── requirements.txt
├── .env                      ← Your keys (create from .env.example)
├── .env.example
├── bot/
│   ├── afk_bot.py            ← Discord self-bot
│   ├── groq_client.py        ← Groq AI integration
│   └── conversation_store.py ← Per-user chat history
└── dashboard/
    ├── app.py                ← Flask + SocketIO server
    └── templates/
        └── index.html        ← Dashboard UI
```

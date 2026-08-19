"""
Stored GIF library — provides categorized GIFs without needing any API key.
"""

import random
import re

# Curated direct GIF links by mood/situation
GIF_COLLECTION = {
    "roast": [
        "https://tenor.com/bDhW2.gif",                                    # Supa hot fire
        "https://tenor.com/bxBKP.gif",                                    # Laughing point
        "https://tenor.com/bDhW2.gif",                                    # Roast / oh
    ],
    "laugh": [
        "https://tenor.com/bQ43V.gif",                                    # Lmao laughing
        "https://tenor.com/b1Cmg.gif",                                    # Spongebob laughing
    ],
    "wave": [
        "https://tenor.com/t5rAQpd0GBf.gif",                              # Hello wave
    ],
    "chill": [
        "https://tenor.com/bV142.gif",                                    # Cat vibing
        "https://tenor.com/bJZ1w.gif",                                    # Kermit sipping tea
    ],
    "afk": [
        "https://tenor.com/bOP2C.gif",                                    # Homer disappearing in bushes
        "https://tenor.com/bSrgX.gif",                                    # Sleeping cat
    ],
    "confused": [
        "https://tenor.com/bEomW.gif",                                    # Confused Travolta
        "https://tenor.com/bB4Gv.gif",                                    # Confused Nick Young
    ],
    "hype": [
        "https://tenor.com/bTj2K.gif",                                    # Excited kid
        "https://tenor.com/bJZ3u.gif",                                    # Minions hype
    ],
    # ── Custom categories ───────────────────────────────────────────
    "scared": [
        "https://tenor.com/vrqJxI8LVIM.gif"
    ],
    "coding_business": [
        "https://tenor.com/lkqW1c3OM5v.gif"
    ],
    "warmed_up": [
        "https://tenor.com/j7aSh5FZXYo.gif"
    ],
    "easy": [
        "https://tenor.com/eCIdM1NVDQm.gif"
    ],
    "gotchu": [
        "https://tenor.com/feVgTfXHHrf.gif"
    ],
    "did_better": [
        "https://tenor.com/rMVomo6bK5C.gif"
    ],
    "gn": [
        "https://tenor.com/muCHwIJMtqt.gif"
    ],
    "gotcha_boss": [
        "https://tenor.com/emZ2jI9cjVI.gif"
    ],
    "not_dead_yet": [
        "https://tenor.com/pSLS9gfLINm.gif"
    ],
    "aura": [
        "https://tenor.com/m1aY4yLw7UN.gif"
    ],
    "back": [
        "https://tenor.com/xraXxkEd2m.gif"
    ],
    "yes": [
        "https://tenor.com/gQs3MVXlSU1.gif"
    ],
    "thank_you": [
        "https://tenor.com/sExu04iLQUn.gif"
    ],
    "hello": [
        "https://tenor.com/t5rAQpd0GBf.gif"
    ]
}


class GifLibrary:
    def __init__(self, custom_gifs: dict = None):
        self.library = dict(GIF_COLLECTION)
        if custom_gifs:
            for category, urls in custom_gifs.items():
                if category in self.library:
                    self.library[category].extend(urls)
                else:
                    self.library[category] = urls

    def get_random_gif(self, mood: str = "chill") -> str:
        """Get a random GIF URL for a mood, with fallback to chill."""
        mood = mood.lower().strip()
        pool = self.library.get(mood) or self.library.get("chill", [])
        if pool:
            return random.choice(pool)
        return ""

    def detect_mood_from_text(self, text: str) -> str:
        """Quick keyword mood detection."""
        t = text.lower()
        # Clean punctuation to get clean words
        words = set(re.sub(r'[^\w\s]', ' ', t).split())
        
        def has_any(keywords):
            for kw in keywords:
                if not kw.isalnum():
                    # If it contains punctuation or spaces, search as substring
                    if kw in t:
                        return True
                else:
                    # If it is a clean single word, match whole word only
                    if kw in words:
                        return True
            return False

        # 1. Custom / specific user-requested situations first
        if has_any(["scared", "afraid", "terrified", "fear", "creepy", "spooked", "horror", "panic"]):
            return "scared"
        if has_any(["warmed up", "warming up", "warm up", "getting warmed"]):
            return "warmed_up"
        if has_any(["gotcha boss", "yes boss", "yes sir", "roger that", "copy that"]):
            return "gotcha_boss"
        if has_any(["gotchu", "got you", "gotch u", "got your back"]):
            return "gotchu"
        if has_any(["already did better", "alrdy did better", "did better", "do better"]):
            return "did_better"
        if has_any(["not dead yet", "am not dead", "still alive", "survived", "still here"]):
            return "not_dead_yet"
        if has_any(["am back", "im back", "i'm back", "returned"]):
            return "back"
        if has_any(["coding", "code", "programming", "programmer", "business", "work", "job", "grind"]):
            return "coding_business"
        if has_any(["easy", "ez", "simple", "piece of cake"]):
            return "easy"
        if has_any(["gn", "goodnight", "good night", "bedtime"]):
            return "gn"
        if has_any(["aura", "drip", "rizz", "cold", "flex"]):
            return "aura"
        if has_any(["thank you", "thanks", "ty", "appreciate", "thx"]):
            return "thank_you"
        if has_any(["yes", "yeah", "yup", "indeed", "absolutely", "ok", "okay"]):
            return "yes"
        if has_any(["hello", "hi", "hey", "yo", "sup", "wassup"]):
            return "hello"

        # 2. Existing / fallback categories
        if has_any(["roast", "clown", "lmao", "trash", "dumb", "ugly", "bot", "loser", "ratio"]):
            return "roast"
        if has_any(["haha", "lol", "xd", "funny", "😂", "🤣"]):
            return "laugh"
        if has_any(["hi", "hello", "hey", "sup", "yo", "wassup"]):
            return "wave"
        if has_any(["afk", "sleep", "bye", "gtg", "cya", "away"]):
            return "afk"
        if has_any(["what", "why", "who", "huh", "?", "confused"]):
            return "confused"
        if has_any(["w", "fire", "hype", "omg", "lets go", "goat", "legend"]):
            return "hype"
        
        return "chill"

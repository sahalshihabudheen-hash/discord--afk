"""
Stored GIF library — provides categorized GIFs without needing any API key.
"""

import random
import re

# Curated direct GIF links by mood/situation
GIF_COLLECTION = {
    "roast": [
        "https://media.giphy.com/media/l8TPBIirERIp2/giphy.gif",          # Supa hot fire / roast
        "https://media.giphy.com/media/xT1XGU1AHz9Fe8tmp2/giphy.gif",      # Mic drop
        "https://media.giphy.com/media/26n6Gx9moCgs1qxxt/giphy.gif",      # Laughing hard
        "https://media.giphy.com/media/j9mqKgQvkNOziGICfd/giphy.gif",      # Side eye / clown
        "https://media.giphy.com/media/A7Zc53i8U59SHv9CAm/giphy.gif",      # Laughing point
    ],
    "laugh": [
        "https://media.giphy.com/media/10JhviFuU2gWD6/giphy.gif",          # Laughing
        "https://media.giphy.com/media/ltIFdjNAasOwVvKhvx/giphy.gif",      # Rolling laughing
        "https://media.giphy.com/media/I4Jmrcjnr8Zfq/giphy.gif",          # Lmao
        "https://media.giphy.com/media/3oEjHAUOqG3lSS0f1C/giphy.gif",      # Muttley laugh
    ],
    "wave": [
        "https://media.giphy.com/media/dzaUX7CAG0Ihi/giphy.gif",          # Hello wave
        "https://media.giphy.com/media/3o7TKWpu2kVMB0150A/giphy.gif",      # Wave hi
        "https://media.giphy.com/media/ASd0Ukj0y3qMM/giphy.gif",          # Cat waving
        "https://media.giphy.com/media/bcKMiwCuBPuQA/giphy.gif",          # Forest Gump wave
    ],
    "chill": [
        "https://media.giphy.com/media/JQXaJaHdd8bVau3oNR/giphy.gif",      # Cat vibing
        "https://media.giphy.com/media/mFYTaY7Gblo8783UXs/giphy.gif",      # Cool glasses
        "https://media.giphy.com/media/3oKIPnAiaMCws8nOsE/giphy.gif",      # Kermit sipping tea
        "https://media.giphy.com/media/g9582DNuQppxC/giphy.gif",          # Gatsby toast
    ],
    "afk": [
        "https://media.giphy.com/media/mguPrVJAnEHIY/giphy.gif",          # Homer disappearing in bushes
        "https://media.giphy.com/media/13HgwGsXF0aiGY/giphy.gif",          # Sleeping cat
        "https://media.giphy.com/media/bC9czlgCMtw4cj8RgH/giphy.gif",      # Spongebob sleeping
        "https://media.giphy.com/media/Ru9sjtZ09XOEg/giphy.gif",          # Peace out disappearing
    ],
    "confused": [
        "https://media.giphy.com/media/lkdH8FmImcGoykgFgz/giphy.gif",      # Confused Nick Young
        "https://media.giphy.com/media/g01ZnwAUvutuK8GIQn/giphy.gif",      # Confused Travolta
        "https://media.giphy.com/media/WRQBXSCnEFJIuxktnw/giphy.gif",      # Math calculation confused
        "https://media.giphy.com/media/kc0kqKNFu7v35gPkwB/giphy.gif",      # Huh?
    ],
    "hype": [
        "https://media.giphy.com/media/artj92V8o75VPL7AeQ/giphy.gif",      # Hyped dance
        "https://media.giphy.com/media/14vh2VWCibnsuk/giphy.gif",          # Let's go
        "https://media.giphy.com/media/ibolLe3mOqHE3PQTtk/giphy.gif",      # Popcorn / excited
        "https://media.giphy.com/media/5GoVLqeAOo6PK/giphy.gif",          # Excited kid
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

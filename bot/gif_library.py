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
        if any(w in t for w in ["roast", "clown", "lmao", "trash", "dumb", "ugly", "bot", "loser", "ratio"]):
            return "roast"
        if any(w in t for w in ["haha", "lol", "xd", "funny", "😂", "🤣"]):
            return "laugh"
        if any(w in t for w in ["hi", "hello", "hey", "sup", "yo", "wassup"]):
            return "wave"
        if any(w in t for w in ["afk", "sleep", "bye", "gtg", "cya", "away"]):
            return "afk"
        if any(w in t for w in ["what", "why", "who", "huh", "?", "confused"]):
            return "confused"
        if any(w in t for w in ["w", "fire", "hype", "omg", "lets go", "goat", "legend"]):
            return "hype"
        return "chill"

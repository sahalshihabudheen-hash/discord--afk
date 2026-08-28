"""
Async AI Image Generator — uses Pollinations FLUX engine (free, no API key required).
"""

import urllib.parse
import aiohttp
import io
import re
from typing import Optional, Tuple


class ImageGenerator:
    def __init__(self):
        self.base_url = "https://image.pollinations.ai/prompt"

    def extract_image_prompt(self, text: str) -> Optional[str]:
        """Check if message is asking for image generation and extract the prompt."""
        t = text.strip()
        
        # Common triggers
        patterns = [
            r"^(?:please\s+)?(?:can\s+you\s+)?(?:generate|create|make|draw|render|paint)\s+(?:an?\s+)?(?:image|picture|photo|artwork|drawing|pic|art)\s+(?:of|about|with|for)?\s*(.+)$",
            r"^(?:draw|generate|paint|render)\s+(?:me\s+)?(?:an?\s+)?(.+)$",
            r"^(?:image|picture|photo|pic|artwork)\s+(?:of|for)\s+(.+)$",
            r"^/imagine\s+(.+)$",
            r"^!imagine\s+(.+)$",
            r"^/draw\s+(.+)$",
            r"^!draw\s+(.+)$",
        ]
        
        for pat in patterns:
            match = re.search(pat, t, re.IGNORECASE)
            if match:
                prompt = match.group(1).strip()
                # Clean leading prepositions
                prompt = re.sub(r"^(?:of|about|for|showing|depicting)\s+", "", prompt, flags=re.IGNORECASE).strip()
                if len(prompt) > 2:
                    return prompt
                    
        return None

    async def generate_image(self, prompt: str, width: int = 1024, height: int = 1024) -> Tuple[Optional[io.BytesIO], str]:
        """Generate image and return (BytesIO buffer, direct_url)."""
        clean_prompt = prompt.strip()
        encoded = urllib.parse.quote(clean_prompt)
        url = f"{self.base_url}/{encoded}?width={width}&height={height}&nologo=true&enhance=true&model=flux"

        try:
            timeout = aiohttp.ClientTimeout(total=45)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")
                        if "image" in content_type:
                            data = await response.read()
                            buffer = io.BytesIO(data)
                            buffer.seek(0)
                            return buffer, url
                        else:
                            print(f"[ImageGen] Non-image response: {content_type}")
                    else:
                        print(f"[ImageGen] HTTP error {response.status} from Pollinations")
        except Exception as e:
            print(f"[ImageGen] Failed to generate image for '{prompt}': {e}")

        return None, url

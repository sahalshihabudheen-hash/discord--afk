"""
Media manager — downloads and permanently stores images and videos from Discord messages.
Provides local storage in dashboard/static/media and base64 data URIs for cloud sync.
"""

import os
import base64
import aiohttp
import mimetypes
from typing import Optional, Dict, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_MEDIA_DIR = os.path.join(BASE_DIR, "dashboard", "static", "media")
WEB_MEDIA_DIR = os.path.join(BASE_DIR, "web", "public", "media")

# Base64 encoding disabled — storing data URIs in conversations.json inflates it to 20-30 MB
# and causes [Errno 22] Invalid argument on Windows. Always use local_url instead.
MAX_BASE64_IMAGE_BYTES = 0

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v", ".mkv"}


def ensure_media_dirs():
    os.makedirs(STATIC_MEDIA_DIR, exist_ok=True)
    if os.path.exists(os.path.join(BASE_DIR, "web", "public")):
        os.makedirs(WEB_MEDIA_DIR, exist_ok=True)


def get_safe_filename(original_name: str, prefix_id: str = "") -> str:
    clean_name = "".join(c for c in original_name if c.isalnum() or c in "._- ")
    if not clean_name:
        clean_name = "media_file"
    if prefix_id:
        return f"{prefix_id}_{clean_name}"
    return clean_name


def is_video_file(filename: str, content_type: Optional[str] = None) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    if ext in VIDEO_EXTENSIONS:
        return True
    if content_type and content_type.startswith("video/"):
        return True
    return False


def is_image_file(filename: str, content_type: Optional[str] = None) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    if ext in IMAGE_EXTENSIONS:
        return True
    if content_type and content_type.startswith("image/"):
        return True
    return False


async def download_bytes(url: str) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        print(f"[MediaManager] Error downloading {url}: {e}")
    return None


async def process_attachment(attachment_obj_or_url, message_id: str = "") -> Dict[str, Any]:
    """
    Downloads and permanently saves an attachment (image or video).
    Returns metadata dict containing original url, local_url, data_url, filename, and flags.
    """
    ensure_media_dirs()

    if hasattr(attachment_obj_or_url, "url"):
        url = attachment_obj_or_url.url
        filename = getattr(attachment_obj_or_url, "filename", "file")
        content_type = getattr(attachment_obj_or_url, "content_type", None)
        file_id = str(getattr(attachment_obj_or_url, "id", message_id or "att"))
        data = None
        try:
            data = await attachment_obj_or_url.read()
        except Exception:
            data = await download_bytes(url)
    else:
        url = str(attachment_obj_or_url)
        url_clean = url.split("?")[0]
        filename = os.path.basename(url_clean) or "attachment"
        file_id = message_id or "att"
        content_type, _ = mimetypes.guess_type(filename)
        data = await download_bytes(url)

    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"

    is_video = is_video_file(filename, content_type)
    is_image = is_image_file(filename, content_type)

    safe_name = get_safe_filename(filename, prefix_id=file_id)
    local_path = os.path.join(STATIC_MEDIA_DIR, safe_name)
    local_url = f"/static/media/{safe_name}"
    data_url = None

    cloud_url = None
    if data:
        try:
            with open(local_path, "wb") as f:
                f.write(data)
            if os.path.exists(WEB_MEDIA_DIR):
                web_path = os.path.join(WEB_MEDIA_DIR, safe_name)
                try:
                    with open(web_path, "wb") as f:
                        f.write(data)
                except Exception:
                    pass
        except Exception as e:
            print(f"[MediaManager] Failed to write local media {local_path}: {e}")

        # Upload to Supabase Storage if configured
        try:
            from bot.supabase_manager import SupabaseManager
            sb = SupabaseManager()
            if sb.enabled:
                cloud_url = await sb.upload_media(data, safe_name, content_type)
        except Exception:
            pass

    return {
        "url": cloud_url or url,
        "local_url": cloud_url or local_url,
        "cloud_url": cloud_url,
        "data_url": None,
        "filename": filename,
        "safe_name": safe_name,
        "content_type": content_type,
        "is_video": is_video,
        "is_image": is_image,
        "size": len(data) if data else 0,
    }

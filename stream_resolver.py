# stream_resolver.py — Automatic Stream Resolver for YouTube Live, RTSP, and Webcams
import time
import re
import threading

# Cache for resolved streams: {url: {"stream_url": str, "title": str, "is_live": bool, "expires_at": float}}
_STREAM_CACHE = {}
_CACHE_LOCK = threading.Lock()
# YouTube HLS manifests expire after several hours; cache for 2 hours
CACHE_TTL = 7200


def is_youtube_url(url):
    """Check if the provided source string is a YouTube URL."""
    if not isinstance(url, str):
        return False
    clean = url.strip().lower()
    return any(domain in clean for domain in [
        "youtube.com/watch",
        "youtube.com/live",
        "youtu.be/",
        "youtube.com/embed",
        "youtube.com/v/"
    ])


def resolve_youtube_stream(url, target_height=720, force_refresh=False):
    """Resolve a YouTube URL or Live Stream to a direct playable OpenCV stream URL.
    
    Args:
        url: The YouTube webpage URL.
        target_height: Preferred video height (e.g. 720 or 480) for optimal AI FPS.
        force_refresh: Ignore cache and re-extract.
        
    Returns:
        tuple: (direct_stream_url, info_dict) or (None, None) on failure.
    """
    url = url.strip()
    now = time.time()

    with _CACHE_LOCK:
        if not force_refresh and url in _STREAM_CACHE:
            cached = _STREAM_CACHE[url]
            if now < cached["expires_at"]:
                return cached["stream_url"], cached["meta"]

    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "nocheckcertificate": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None, None

            title = info.get("title", "YouTube Live Stream")
            is_live = bool(info.get("is_live", False))

            formats = [
                f for f in info.get("formats", [])
                if f.get("vcodec") != "none" and f.get("url")
            ]

            selected_url = None
            if formats:
                # Find best format <= target_height (e.g., 720p) for high frame rate YOLO
                suitable = [f for f in formats if (f.get("height") or 0) <= target_height]
                if suitable:
                    chosen = max(suitable, key=lambda f: f.get("height") or 0)
                else:
                    # Fallback to the lowest available video format to preserve CPU
                    chosen = formats[0]
                selected_url = chosen.get("url")
            else:
                selected_url = info.get("url")

            if not selected_url:
                return None, None

            meta = {
                "title": title,
                "is_live": is_live,
                "author": info.get("uploader") or info.get("channel") or "",
                "duration": info.get("duration", 0),
                "resolution": f"{target_height}p"
            }

            with _CACHE_LOCK:
                _STREAM_CACHE[url] = {
                    "stream_url": selected_url,
                    "meta": meta,
                    "expires_at": now + CACHE_TTL
                }

            return selected_url, meta

    except Exception as e:
        print(f"⚠️ Failed to resolve YouTube stream ({url}): {e}")
        return None, None


def resolve_stream_source(source, target_height=720):
    """Normalize any source (device index, RTSP, file, or YouTube URL) for cv2.VideoCapture.
    
    Returns:
        tuple: (cv2_compatible_source, metadata_dict)
    """
    if source is None:
        return 0, {"title": "Default Camera", "type": "webcam"}

    # Numerical webcam index
    if isinstance(source, int):
        return source, {"title": f"Webcam Device {source}", "type": "webcam"}
    if isinstance(source, str) and source.isdigit():
        return int(source), {"title": f"Webcam Device {source}", "type": "webcam"}

    source_str = str(source).strip()

    # YouTube URL
    if is_youtube_url(source_str):
        direct_url, meta = resolve_youtube_stream(source_str, target_height=target_height)
        if direct_url:
            meta["type"] = "youtube"
            meta["original_source"] = source_str
            return direct_url, meta
        else:
            return source_str, {"title": "YouTube (Unresolved)", "type": "youtube", "original_source": source_str}

    # RTSP / HTTP Network stream or local file
    title = "RTSP Stream" if source_str.lower().startswith("rtsp://") else "Network / Video Source"
    return source_str, {"title": title, "type": "network", "original_source": source_str}

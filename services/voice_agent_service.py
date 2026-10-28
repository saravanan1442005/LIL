"""Voice Agent AI Service for Gate Tablet Kiosk.
Supports Tamil & English conversational voice check-in, intent and entity extraction
(Visitor name, purpose/work, expected dwell duration, phone number),
integrating with Gemini API if available with a fast resilient local fallback.
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ecolifybuddy.voice")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

_TTS_CACHE_DIR = None


def generate_tts_audio_bytes(text: str, lang: str = "ta") -> bytes:
    """Generate or retrieve cached natural Tamil/English MP3 audio bytes using gTTS."""
    import io
    import hashlib
    from pathlib import Path
    from gtts import gTTS

    global _TTS_CACHE_DIR
    if _TTS_CACHE_DIR is None:
        _TTS_CACHE_DIR = Path("data") / "tts_cache"
        _TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    text = str(text or "").strip()
    if not text:
        return b""

    lang_code = "ta" if "ta" in lang.lower() else "en"
    key = hashlib.md5(f"{lang_code}:{text}".encode("utf-8")).hexdigest()
    cache_path = _TTS_CACHE_DIR / f"{key}.mp3"

    if cache_path.exists():
        try:
            return cache_path.read_bytes()
        except Exception:
            pass

    try:
        tts = gTTS(text=text, lang=lang_code)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        data = buf.getvalue()
        try:
            cache_path.write_bytes(data)
        except Exception:
            pass
        return data
    except Exception as e:
        logger.warning("gTTS audio generation error for '%s': %s", text, e)
        return b""


def transcribe_and_extract_from_audio_bytes(audio_bytes: bytes, language: str = "ta-IN") -> Dict[str, Any]:
    """Transcribe raw WAV audio bytes using Google Speech Recognition in Tamil / English,
    then extract visitor entities (name, purpose, duration, phone).
    """
    import io
    import speech_recognition as sr

    r = sr.Recognizer()
    transcript = ""
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = r.record(source)
            try:
                transcript = r.recognize_google(audio, language=language)
            except sr.UnknownValueError:
                if language.startswith("ta"):
                    try:
                        transcript = r.recognize_google(audio, language="en-IN")
                    except Exception:
                        transcript = ""
                else:
                    transcript = ""
            except Exception as ex:
                logger.warning("Google STT network error: %s", ex)
                transcript = ""
    except Exception as e:
        logger.warning("Failed to decode audio file: %s", e)
        transcript = ""

    extracted = extract_visitor_details_from_speech(transcript, language=language)
    extracted["raw_transcript"] = transcript
    return extracted


def extract_visitor_details_from_speech(transcript: str, language: str = "ta-IN") -> Dict[str, Any]:
    """Parse visitor speech in Tamil or English to extract:
    - name: Visitor name
    - purpose: Reason for visit (Delivery, Electrician, Cleaning, Guest, etc.)
    - company: Zomato, Swiggy, Amazon, Porter, Urban Company, etc.
    - expected_duration_minutes: Estimated stay time in minutes (default 30-60)
    - phone: 10-digit phone number if spoken
    """
    transcript = str(transcript or "").strip()
    if not transcript:
        return {
            "name": None,
            "purpose": "Visitor",
            "company": None,
            "expected_duration_minutes": 30,
            "phone": None,
            "language": language,
            "raw_transcript": transcript,
        }

    # 1. Try Gemini API if API key is present
    if GEMINI_API_KEY:
        try:
            return _extract_with_gemini(transcript, language)
        except Exception as e:
            logger.warning("Gemini voice extraction fallback triggered: %s", e)

    # 2. Resilient Rule-based / Regex NLP parser (100% Free & Fast)
    return _extract_with_rules(transcript, language)


def _extract_with_gemini(transcript: str, language: str) -> Dict[str, Any]:
    """Use Gemini Flash to structure visitor intent and details from spoken text."""
    import urllib.request
    import json

    prompt = f"""You are a gate security voice assistant at an apartment complex.
The visitor spoke the following statement in {language}:
"{transcript}"

Extract the visitor details into a JSON object with these exact keys:
- "name": visitor's name (string or null)
- "purpose": specific purpose like "Delivery", "Plumber", "Electrician", "House Maid", "Guest", "Maintenance", "Courier" (string)
- "company": delivery/vendor company like "Swiggy", "Zomato", "Amazon", "Flipkart", "Dunzo", "Porter", "Urban Company" if mentioned (string or null)
- "expected_duration_minutes": integer number of minutes they said they will stay (e.g., 30 for half an hour, 60 for 1 hour, 15 for 15 minutes. Default to 30 if not mentioned)
- "phone": 10-digit mobile number if spoken (digits only, or null)
- "reply_tamil": polite short response in Tamil welcoming them or asking for missing info (string)
- "reply_english": English translation of the reply (string)

Return ONLY valid JSON without markdown wrapping."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        text_content = result["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_content.strip())
        parsed["raw_transcript"] = transcript
        parsed["language"] = language
        return parsed


def _extract_with_rules(transcript: str, language: str) -> Dict[str, Any]:
    """Robust zero-cost extraction for Tamil & English speech."""
    text_lower = transcript.lower()

    # Extract phone digits if mentioned
    digits = "".join(ch for ch in transcript if ch.isdigit())
    phone = digits if len(digits) >= 10 else None

    # Detect Company
    company = None
    known_companies = {
        "swiggy": "Swiggy",
        "zomato": "Zomato",
        "amazon": "Amazon",
        "flipkart": "Flipkart",
        "zepto": "Zepto",
        "blinkit": "Blinkit",
        "dunzo": "Dunzo",
        "uber": "Uber",
        "ola": "Ola",
        "porter": "Porter",
        "urban": "Urban Company",
        "ஸ்விக்கி": "Swiggy",
        "ஜொமேட்டோ": "Zomato",
        "ஜொமாட்டோ": "Zomato",
        "அமேசான்": "Amazon",
        "ஃபிளிப்கார்ட்": "Flipkart",
        "ஜெப்டோ": "Zepto",
        "பிளின்கிட்": "Blinkit",
        "டன்சோ": "Dunzo",
    }
    for keyword, comp_name in known_companies.items():
        if keyword in text_lower or keyword in transcript:
            company = comp_name
            break

    # Detect Purpose / Work
    purpose = "Delivery" if company else "Visitor"
    if any(k in text_lower for k in ["food", "food delivery", "ஃபுட்", "ஃபுட் டெலிவரி", "சாப்பாடு", "உணவு", "பார்சல்", "டெலிவரி", "parcel", "courier"]):
        purpose = "Delivery"
    elif any(k in text_lower for k in ["electric", "electrician", "கரண்ட்", "எலக்ட்ரீசியன்"]):
        purpose = "Electrician"
    elif any(k in text_lower for k in ["plumb", "plumber", "பைப்", "பிளம்பர்"]):
        purpose = "Plumber"
    elif any(k in text_lower for k in ["clean", "maid", "வீட்டு வேலை", "சுத்தம்"]):
        purpose = "Housekeeping"
    elif any(k in text_lower for k in ["friend", "relative", "சொந்தக்காரர்", "விருந்தினர்", "guest", "பார்க்க வந்தேன்"]):
        purpose = "Guest"

    # Detect Duration
    duration = 30
    if any(k in text_lower for k in ["half an hour", "30 min", "30 நிமிடம்", "30 நிமிஷம்", "அரை மணி", "அரை மணி நேரம்"]):
        duration = 30
    elif any(k in text_lower for k in ["1 hour", "one hour", "ஒரு மணி", "ஒரு மணி நேரம்", "60 min", "60 நிமிடம்", "60 நிமிஷம்"]):
        duration = 60
    elif any(k in text_lower for k in ["2 hour", "two hours", "ரெண்டு மணி", "இரண்டு மணி"]):
        duration = 120
    elif any(k in text_lower for k in ["10 min", "15 min", "15 நிமிடம்", "15 நிமிஷம்", "10 நிமிடம்"]):
        duration = 15
    else:
        # Check digit + minutes regex
        match = re.search(r"(\d+)\s*(?:mins?|minutes?|நிமிடம்|நிமிஷம்)", text_lower)
        if match:
            try:
                duration = int(match.group(1))
            except ValueError:
                duration = 30

    # Detect Name
    name = None
    name_patterns = [
        r"(?:என் பெயர்|பெயர்|name is|i am)\s+([A-Za-z\u0B80-\u0BFF]+)",
        r"(?:நான்|i am)\s+([A-Za-z\u0B80-\u0BFF]+)\s+(?:ஸ்விக்கி|ஜொமேட்டோ|delivery|from|இங்கே|வந்திருக்கேன்)",
        r"^([A-Za-z\u0B80-\u0BFF]+)\s+(?:from|இங்கே|வந்திருக்கேன்)",
    ]
    stopwords = {
        "delivery", "swiggy", "zomato", "amazon", "naan", "நான்", "வணக்கம்", "vanakkam", 
        "இங்கே", "இங்க", "வந்திருக்கேன்", "வந்துள்ளேன்", "பண்ண", "செய்ய", "ஃபுட்", "சாப்பாடு",
        "வேலை", "பார்க்க", "போக", "ஆகும்", "மணி", "நிமிஷம்", "நிமிடம்", "டெலிவரி"
    }
    for pattern in name_patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) > 2 and candidate.lower() not in stopwords:
                name = candidate.title()
                break

    if not name:
        words = transcript.split()
        for w in words:
            w_clean = re.sub(r"[^\w\u0B80-\u0BFF]", "", w)
            if len(w_clean) > 2 and w_clean.lower() not in stopwords and not w_clean.isdigit():
                name = w_clean.title()
                break

    reply_tamil = f"நன்றி {name or ''}! உங்கள் வருகை பதிவு செய்யப்படுகிறது."
    reply_english = f"Thank you {name or ''}! Logging your visit."

    return {
        "name": name,
        "purpose": purpose,
        "company": company,
        "expected_duration_minutes": duration,
        "phone": phone,
        "reply_tamil": reply_tamil,
        "reply_english": reply_english,
        "raw_transcript": transcript,
        "language": language,
    }

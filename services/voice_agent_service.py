"""Voice Agent AI Service for Gate Tablet Kiosk.
Supports Tamil & English conversational voice check-in, intent and entity extraction
(Visitor name, purpose/work, expected dwell duration, phone number),
integrating with Gemini API if available with a fast resilient local fallback.
"""

import os
import re
import json
import io
import hashlib
import urllib.request
import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from gtts import gTTS  # pyrefly: ignore[missing-import]  # type: ignore
except ImportError:
    gTTS = None  # type: ignore

try:
    import speech_recognition as sr  # pyrefly: ignore[missing-import]  # type: ignore
except ImportError:
    sr = None  # type: ignore

logger = logging.getLogger("ecolifybuddy.voice")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

_TTS_CACHE_DIR: Optional[Path] = None


def generate_tts_audio_bytes(text: Optional[str] = "", lang: str = "ta") -> bytes:
    """Generate or retrieve cached natural Tamil/English MP3 audio bytes using gTTS."""
    global _TTS_CACHE_DIR
    if _TTS_CACHE_DIR is None:
        _TTS_CACHE_DIR = Path("data") / "tts_cache"
        _TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    clean_text = str(text or "").strip()
    if not clean_text or gTTS is None:
        return b""

    lang_code = "ta" if "ta" in lang.lower() else "en"
    key = hashlib.md5(f"{lang_code}:{clean_text}".encode("utf-8")).hexdigest()
    cache_path = _TTS_CACHE_DIR / f"{key}.mp3"

    if cache_path.exists():
        try:
            return cache_path.read_bytes()
        except Exception:
            pass

    try:
        tts = gTTS(text=clean_text, lang=lang_code)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        data = buf.getvalue()
        try:
            cache_path.write_bytes(data)
        except Exception:
            pass
        return data
    except Exception as e:
        logger.warning("gTTS audio generation error for '%s': %s", clean_text, e)
        return b""


def transcribe_and_extract_from_audio_bytes(audio_bytes: bytes, language: str = "ta-IN") -> Dict[str, Any]:
    """Transcribe raw WAV audio bytes using Google Speech Recognition in Tamil / English,
    then extract visitor entities (name, purpose, duration, phone).
    """
    if sr is None:
        logger.warning("speech_recognition module is not available")
        extracted = extract_visitor_details_from_speech("", language=language)
        extracted["raw_transcript"] = ""
        return extracted

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


def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def classify_confirmation_intent(text: str) -> Optional[bool]:
    """Classify visitor's confirmation response as positive (True), negative (False), or undecided (None).
    Handles both Tamil and English spoken intents for entry/exit confirmations.
    """
    if not text:
        return None
    cleaned = text.strip().lower()

    # Negative tokens checked first to avoid false positives (e.g. "இல்லை, நான் நுழையவில்லை")
    negative_patterns = [
        r"இல்லை", r"இல்ல", r"இல்லங்க", r"வேண்டாம்", r"வேணாம்", r"நுழையவில்லை", r"வெளியேறவில்லை",
        r"தவறு", r"நோ", r"இப்ப இல்ல", r"இப்ப வேண்டாம்", r"வேணாங்க", r"வேண்டாங்க",
        r"\bno\b", r"\bnope\b", r"\bnot\s+now\b", r"\bnot\s+entering\b", r"\bnot\s+leaving\b",
        r"\bcancel\b", r"\bdon'?t\b", r"\bstop\b", r"\bnegative\b", r"\bwrong\b", r"\bnever\b"
    ]
    for pattern in negative_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return False

    positive_patterns = [
        r"ஆம்", r"ஆமாம்", r"ஆமா", r"சரி", r"நுழைகிறேன்", r"வெளியேறுகிறேன்", r"உள்ள போறேன்", r"வெளிய போறேன்",
        r"ஓகே", r"எஸ்", r"கண்டிப்பா", r"ஆமாங்க", r"சரிங்க", r"போறேன்", r"போகிறேன்", r"உள்ளே செல்கிறேன்",
        r"வெளியே செல்கிறேன்", r"உள்ள போலாம்", r"உள்ளே", r"வெளியே", r"நுழைய", r"வெளியேற",
        r"\byes\b", r"\byeah\b", r"\byep\b", r"\byup\b", r"\bsure\b", r"\bok\b", r"\bokay\b",
        r"\bcorrect\b", r"\bconfirm\b", r"\benter\b", r"\bexit\b", r"\bproceed\b", r"\bright\b",
        r"\baffirmative\b", r"\bentering\b", r"\bleaving\b"
    ]
    for pattern in positive_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return True

    return None


def conduct_visitor_conversation(
    transcript: str,
    existing_data: Optional[Dict[str, Any]] = None,
    language: str = "ta-IN"
) -> Dict[str, Any]:
    """Adaptive multi-turn conversational AI dialogue manager for gate kiosk.
    Delegates to the Google ADK Agent orchestrator for tool-driven validation and dialogue.
    """
    try:
        from services.kiosk_adk_agent import get_kiosk_adk_agent
        adk_agent = get_kiosk_adk_agent()
        return adk_agent.process_turn(transcript, existing_data=existing_data, language=language)
    except Exception as e:
        logger.warning("Falling back from ADK agent to rule dialogue: %s", e)

    if existing_data is None:
        existing_data = {}

    extracted = extract_visitor_details_from_speech(transcript, language=language)

    # Merge newly extracted non-empty fields
    merged = dict(existing_data)
    if extracted.get("name") and not merged.get("name"):
        merged["name"] = extracted["name"]
    if extracted.get("company") and not merged.get("company"):
        merged["company"] = extracted["company"]
    if extracted.get("purpose") and extracted["purpose"] not in ("Visitor", "Other", None):
        merged["purpose"] = extracted["purpose"]
    elif merged.get("company") and (not merged.get("purpose") or merged.get("purpose") == "Visitor"):
        merged["purpose"] = "Delivery"

    # If duration specifically detected in this turn, update it
    turn_dur = extracted.get("expected_duration_minutes")
    if turn_dur:
        merged["expected_duration_minutes"] = turn_dur

    if extracted.get("phone") and not merged.get("phone"):
        merged["phone"] = extracted["phone"]

    # Check completeness
    has_name = bool(merged.get("name"))
    has_purpose = bool(merged.get("company") or (merged.get("purpose") and merged["purpose"] != "Visitor"))
    raw_phone_digits = "".join(ch for ch in str(merged.get("phone") or "") if ch.isdigit())
    has_phone = len(raw_phone_digits) >= 10
    has_duration = bool(merged.get("expected_duration_minutes"))

    name_str = merged.get("name", "")

    if not has_name and not has_purpose:
        is_complete = False
        reply_ta = "வணக்கம்! உங்கள் பெயர், எதற்காக வந்திருக்கிறீர்கள், மொபைல் எண் மற்றும் எவ்வளவு நேரம் உள்ளே இருப்பீர்கள் என்று கூறுங்கள்?"
        reply_en = "Welcome! What is your name, purpose of visit, mobile number, and how long will you stay inside?"
    elif not has_name:
        is_complete = False
        if not has_duration:
            reply_ta = "சரி! உங்கள் பெயர் மற்றும் எவ்வளவு நேரம் உள்ளே இருப்பீர்கள் என்று கூறுங்கள்?"
            reply_en = "Got it! Please share your name and how long you will stay inside."
        else:
            reply_ta = "சரி! உங்கள் பெயர் என்ன என்று கூறுங்கள்?"
            reply_en = "Got it! What is your name?"
    elif not has_purpose:
        is_complete = False
        if not has_duration:
            reply_ta = f"சரி {name_str}! நீங்கள் எதற்காக வந்திருக்கிறீர்கள் மற்றும் எவ்வளவு நேரம் வளாகத்தில் இருப்பீர்கள்?"
            reply_en = f"Alright {name_str}! What is the purpose of your visit and how long will you stay?"
        else:
            reply_ta = f"சரி {name_str}! நீங்கள் எதற்காக வந்திருக்கிறீர்கள்? டெலிவரி, வேலை அல்லது விருந்தினரா?"
            reply_en = f"Alright {name_str}! What is the purpose of your visit? Delivery, work, or guest?"
    elif not has_phone:
        is_complete = False
        if not has_duration:
            reply_ta = f"சரி {name_str}! உங்களது 10 இலக்க மொபைல் எண் மற்றும் எவ்வளவு நேரம் உள்ளே இருப்பீர்கள் என்று கூறுங்கள்?"
            reply_en = f"Alright {name_str}! Please share your 10-digit mobile number and expected stay duration."
        else:
            reply_ta = f"சரி {name_str}! உங்களது 10 இலக்க மொபைல் எண் என்ன என்று கூறுங்கள்?"
            reply_en = f"Alright {name_str}! Please share your 10-digit mobile number."
    elif not has_duration:
        is_complete = False
        reply_ta = f"சரி {name_str}! நீங்கள் வளாகத்தில் எவ்வளவு நேரம் இருப்பீர்கள்? 10 நிமிடமா, 30 நிமிடமா, அல்லது 1 மணி நேரமா?"
        reply_en = f"Alright {name_str}! How long will you stay inside? 10 minutes, 30 minutes, or 1 hour?"
    else:
        # ALL COMPLETE!
        is_complete = True
        dur_mins = merged.get("expected_duration_minutes") or 30
        if dur_mins >= 1440:
            days = dur_mins // 1440
            dur_txt_ta = f"{days} நாட்கள்" if days > 1 else "1 நாள்"
            dur_txt_en = f"{days} days" if days > 1 else "1 day"
        elif dur_mins >= 60:
            hrs = dur_mins // 60
            dur_txt_ta = f"{hrs} மணி நேரம்"
            dur_txt_en = f"{hrs} hour{'s' if hrs > 1 else ''}"
        else:
            dur_txt_ta = f"{dur_mins} நிமிடங்கள்"
            dur_txt_en = f"{dur_mins} minutes"
        reply_ta = f"சரி {name_str}! உங்கள் விவரங்கள் பதிவு செய்யப்பட்டுவிட்டது. நீங்கள் உள்ளே போகலாம்!"
        reply_en = f"Alright {name_str}! Your details are registered for {dur_txt_en}. You may proceed inside!"

    return {
        "updated_data": merged,
        "is_complete": is_complete,
        "reply_tamil": reply_ta,
        "reply_english": reply_en,
        "raw_transcript": transcript,
    }


def get_gemini_live_session_config() -> Dict[str, Any]:
    """Return configuration payload for the Gemini Multimodal Live API
    (https://ai.google.dev/gemini-api/docs/live-api).
    Used to establish real-time bidirectional WebSocket sessions directly from client or gateway.
    """
    key = get_gemini_api_key()
    return {
        "model": "models/gemini-2.0-flash-exp",
        "ws_url": f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={key}",
        "api_key_masked": f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***",
        "has_api_key": bool(key),
        "setup_message": {
            "setup": {
                "model": "models/gemini-2.0-flash-exp",
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": "Puck"
                            }
                        }
                    }
                },
                "systemInstruction": {
                    "parts": [
                        {
                            "text": (
                                "You are an autonomous AI Gate Security Reception Agent at an apartment & commercial community. "
                                "Greet visitors in Tamil and English. Ask their name, purpose of visit (Delivery, Electrician, Plumber, Guest), "
                                "and expected duration (minutes or hours). Keep responses concise, warm, and professional."
                            )
                        }
                    ]
                },
                "tools": [
                    {
                        "functionDeclarations": [
                            {
                                "name": "register_visitor",
                                "description": "Registers approved visitor with name, purpose, company and duration in minutes.",
                                "parameters": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "name": {"type": "STRING", "description": "Visitor full name"},
                                        "purpose": {"type": "STRING", "description": "Purpose of visit e.g. Delivery, Guest, Maintenance"},
                                        "company": {"type": "STRING", "description": "Company name e.g. Swiggy, Zomato, Amazon if applicable"},
                                        "duration_minutes": {"type": "INTEGER", "description": "Stay duration in minutes e.g. 30, 60, 120"}
                                    },
                                    "required": ["name", "purpose", "duration_minutes"]
                                }
                            }
                        ]
                    }
                ]
            }
        }
    }



def extract_visitor_details_from_speech(transcript: str, language: str = "ta-IN") -> Dict[str, Any]:
    """Parse visitor speech in Tamil or English to extract:
    - name: Visitor name
    - purpose: Reason for visit (Delivery, Electrician, Cleaning, Guest, etc.)
    - company: Zomato, Swiggy, Amazon, Porter, Urban Company, etc.
    - expected_duration_minutes: Estimated stay time in minutes (hours converted to minutes)
    - phone: 10-digit phone number if spoken
    """
    transcript = str(transcript or "").strip()
    if not transcript:
        return {
            "name": None,
            "purpose": "Visitor",
            "company": None,
            "expected_duration_minutes": None,
            "phone": None,
            "language": language,
            "raw_transcript": transcript,
            "reply_tamil": "வணக்கம்! உங்கள் பெயர் மற்றும் வருகை நோக்கத்தைக் கூறவும்.",
            "reply_english": "Welcome! Please tell us your name and purpose of visit.",
        }

    # 1. Try Gemini API with fast 3.5s timeout
    key = get_gemini_api_key()
    if key:
        try:
            return _extract_with_gemini(transcript, language, key)
        except Exception as e:
            logger.info("Gemini voice extraction fallback: %s", e)

    # 2. Resilient Rule-based / Regex NLP parser (Instant & Zero Network Lag)
    return _extract_with_rules(transcript, language)


def _extract_with_gemini(transcript: str, language: str, key: str) -> Dict[str, Any]:
    """Use Gemini 3.1 Flash Lite to parse visitor intent and details from spoken text."""
    prompt = f"""You are a gate security voice assistant at an apartment/community complex.
The visitor spoke:
"{transcript}"
Spoken language or dialect: {language}.

Extract details into a JSON object:
- "name": visitor's name (string or null)
- "purpose": specific purpose ONLY IF STATED like "Delivery", "Plumber", "Electrician", "Housekeeping", "Maintenance", "Vendor", "Guest" (string or null). If they only gave their name and did not say why they came, set "purpose": null.
- "company": delivery/vendor company like "Swiggy", "Zomato", "Amazon", "Flipkart", "Dunzo", "Porter", "Zepto", "Blinkit" if mentioned (string or null)
- "expected_duration_minutes": integer number of minutes they said they will stay (e.g. 1 hour -> 60, 2 hours -> 120, half an hour / 30 mins -> 30, 15 mins -> 15, 1 day -> 1440, 2 days -> 2880, 3 days -> 4320, 1 week -> 10080. If they said days or hours, convert to total minutes. If not stated, set null)
- "phone": 10-digit mobile number if spoken (digits only, or null)
- "reply_tamil": polite short response in Tamil welcoming them or asking what they need (string)
- "reply_english": English translation of the reply (string)

Return ONLY valid JSON."""

    model = "models/gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=3.5) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        text_content = result["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_content.strip())
        parsed["raw_transcript"] = transcript
        parsed["language"] = language
        # Ensure duration is an integer or None
        try:
            raw_dur = parsed.get("expected_duration_minutes")
            parsed["expected_duration_minutes"] = int(raw_dur) if raw_dur is not None else None
        except (ValueError, TypeError):
            parsed["expected_duration_minutes"] = None
        return parsed


def _extract_with_rules(transcript: str, language: str) -> Dict[str, Any]:
    """Robust zero-cost extraction for Tamil & English speech with full hour/minute support."""
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

    # Detect Duration in Minutes, Hours, or Days (None if not mentioned)
    duration = None

    # Common spoken phrases in Tamil & English (minutes, hours, fractions, days, weeks)
    duration_phrases = [
        (["1 day", "one day", "ஒரு நாள்", "1 நாள்", "full day", "முழு நாள்", "இன்று முழுவதும்", "இன்னைக்கு முழுவதும்", "இன்னைக்கு முழுதும்"], 1440),
        (["2 days", "two days", "ரெண்டு நாள்", "இரண்டு நாள்", "2 நாள்", "ரெண்டு நாட்கள்", "இரண்டு நாட்கள்", "2 நாட்கள்"], 2880),
        (["3 days", "three days", "மூன்று நாள்", "மூணு நாள்", "3 நாள்", "மூன்று நாட்கள்", "3 நாட்கள்"], 4320),
        (["4 days", "four days", "4 நாட்கள்", "நான்கு நாட்கள்"], 5760),
        (["5 days", "five days", "5 நாட்கள்", "ஐந்து நாட்கள்"], 7200),
        (["1 week", "one week", "a week", "ஒரு வாரம்", "1 வாரம்"], 10080),
        (["2 weeks", "two weeks", "ரெண்டு வாரம்", "இரண்டு வாரம்", "2 வாரம்"], 20160),
        (["ஒரு மணி", "ஒரு மணி நேரம்", "1 hour", "one hour", "ஒன் ஹவர்", "ஒன் அவர்", "an hour"], 60),
        (["இரண்டு மணி", "ரெண்டு மணி", "ரெண்டு மணி நேரம்", "2 hours", "two hours", "டூ ஹவர்", "டூ அவர்"], 120),
        (["மூன்று மணி", "மூணு மணி", "மூணு மணி நேரம்", "3 hours", "three hours"], 180),
        (["ஒன்றரை மணி", "ஒன்றரை மணி நேரம்", "1.5 hours", "one and half hour"], 90),
        (["அரை மணி", "அரை மணி நேரம்", "half an hour", "half hour", "ஹாப் அன் ஹவர்", "ஹாஃப் அன் ஹவர்"], 30),
        (["கால் மணி", "கால் மணி நேரம்", "quarter hour"], 15),
        (["முக்கால் மணி", "முக்கால் மணி நேரம்"], 45),
        (["பத்து நிமிடம்", "பத்து நிமிடங்கள்", "பத்து நிமிஷம்", "10 min", "10 mins"], 10),
        (["பதினைந்து நிமிடம்", "பதினைந்து நிமிடங்கள்", "பதினைஞ்சு நிமிஷம்", "15 min", "15 mins"], 15),
        (["இருபது நிமிடம்", "இருபது நிமிடங்கள்", "இருவது நிமிஷம்", "20 min", "20 mins"], 20),
        (["முப்பது நிமிடம்", "முப்பது நிமிடங்கள்", "முப்பது நிமிஷம்", "30 min", "30 mins"], 30),
        (["நாற்பத்தைந்து நிமிடம்", "நாற்பத்தைந்து நிமிடங்கள்", "நாற்பத்தைஞ்சு நிமிஷம்", "45 min", "45 mins"], 45),
        (["அறுபது நிமிடம்", "அறுபது நிமிடங்கள்", "அறுவது நிமிஷம்", "60 min", "60 mins"], 60),
    ]
    for keywords, dur in duration_phrases:
        if any(k in text_lower for k in keywords):
            duration = dur
            break

    if duration is None:
        # 1. Check days regex (e.g. "2 days", "for 2 days", "3 நாட்கள்", "2 நாள்")
        day_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:days?|நாட்கள்|நாள்\w*)", text_lower)
        if day_match:
            try:
                duration = int(float(day_match.group(1)) * 1440)
            except ValueError:
                duration = 1440
        else:
            # 2. Check weeks regex (e.g. "1 week", "2 weeks", "ஒரு வாரம்")
            week_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:weeks?|வார\w*)", text_lower)
            if week_match:
                try:
                    duration = int(float(week_match.group(1)) * 10080)
                except ValueError:
                    duration = 10080
            else:
                # 3. Check hours regex (e.g. 1 hour, 2 மணி, 1.5 மணி நேரம்)
                hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|மணி\w*)", text_lower)
                if hour_match:
                    try:
                        duration = int(float(hour_match.group(1)) * 60)
                    except ValueError:
                        duration = 60
                else:
                    # 4. Check minutes regex (e.g. 10 நிமிடங்கள், 15 நிமிஷம், 30 minutes, 45 mins)
                    min_match = re.search(r"(\d+)\s*(?:mins?|minutes?|நிமிட\w*|நிமிஷ\w*)", text_lower)
                    if min_match:
                        try:
                            duration = int(min_match.group(1))
                        except ValueError:
                            duration = 30
                    else:
                        # 5. Standalone spoken digits / words (when answering duration question)
                        stripped = text_lower.strip()
                        if stripped.isdigit():
                            val = int(stripped)
                            if val in [1, 2, 3]:
                                duration = val * 60  # e.g., "1" or "2" usually means hours
                            elif val in [5, 10, 15, 20, 25, 30, 40, 45, 60, 90, 120]:
                                duration = val
                        elif stripped in ["one", "ஒன்று"]:
                            duration = 60
                        elif stripped in ["two", "இரண்டு", "ரெண்டு"]:
                            duration = 120

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
        "வேலை", "பார்க்க", "போக", "ஆகும்", "மணி", "நிமிஷம்", "நிமிடம்", "டெலிவரி", "ஒரு", "ரெண்டு",
        "hour", "hours", "hr", "hrs", "min", "mins", "minute", "minutes", "time", "stay"
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

    if duration is not None:
        if duration >= 1440:
            days = duration // 1440
            dur_text = f"{days} நாட்கள்" if days > 1 else "1 நாள்"
            dur_en = f"{days} days" if days > 1 else "1 day"
        elif duration >= 60:
            hrs = duration // 60
            dur_text = f"{hrs} மணி நேரம்"
            dur_en = f"{hrs} hour{'s' if hrs > 1 else ''}"
        else:
            dur_text = f"{duration} நிமிடங்கள்"
            dur_en = f"{duration} minutes"
        reply_tamil = f"நன்றி {name or ''}! உங்கள் வருகை {dur_text} வரை பதிவு செய்யப்படுகிறது."
        reply_english = f"Thank you {name or ''}! Logging your visit for {dur_en}."
    else:
        reply_tamil = f"நன்றி {name or ''}! உங்கள் விவரங்கள் பெறப்பட்டது."
        reply_english = f"Thank you {name or ''}! Details received."

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


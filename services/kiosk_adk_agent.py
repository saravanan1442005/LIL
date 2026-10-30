"""Kiosk ADK Agent Service (Google ADK Architecture & Tool Orchestration).
Follows https://adk.dev/ specifications:
- Software engineering-first design with explicit tool definitions & type annotations
- Autonomous visitor check-in, purpose extraction, duration validation & overstay calculation
- Resilient fallback execution engine if offline or google-adk package is not natively imported
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ecolifybuddy.adk_agent")

# Try importing google-adk if available in environment
try:
    from google.adk import Agent, tool  # type: ignore
    HAS_GOOGLE_ADK = True
except Exception:
    HAS_GOOGLE_ADK = False

# ---------------------------------------------------------------------------
# ADK Tools for Gate Kiosk Agent
# ---------------------------------------------------------------------------

def validate_and_format_duration(duration_minutes: int, purpose: str = "Visitor") -> Dict[str, Any]:
    """Validate and compute allowed stay duration based on visitor purpose.
    Delivery: typically 15-30 minutes.
    Maintenance/Electrician/Plumber: 60-180 minutes.
    Guest: 30-240 minutes.
    """
    mins = int(duration_minutes or 30)
    mins = max(5, min(mins, 20160)) # Clamp between 5m and 14 days
    
    purp_lower = (purpose or "").lower()
    is_standard = True
    note = "Standard requested duration approved."

    if any(k in purp_lower for k in ["delivery", "swiggy", "zomato", "amazon", "zepto", "courier", "food"]):
        if mins > 45:
            is_standard = False
            note = f"Delivery usually takes under 30 mins; allowed {mins} mins with security notice."
    elif any(k in purp_lower for k in ["electrician", "plumber", "repair", "service", "maintenance"]):
        if mins < 30:
            mins = 60
            note = "Maintenance minimum visit duration set to 60 mins."

    if mins >= 1440:
        d = mins // 1440
        txt_ta = f"{d} நாட்கள்" if d > 1 else "1 நாள்"
        txt_en = f"{d} days" if d > 1 else "1 day"
    elif mins >= 60:
        h = mins // 60
        txt_ta = f"{h} மணி நேரம்"
        txt_en = f"{h} hour(s)"
    else:
        txt_ta = f"{mins} நிமிடங்கள்"
        txt_en = f"{mins} minutes"

    return {
        "approved_duration_minutes": mins,
        "is_standard": is_standard,
        "policy_note": note,
        "formatted_text_ta": txt_ta,
        "formatted_text_en": txt_en
    }


def lookup_visitor_history(phone: Optional[str] = None, visitor_name: Optional[str] = None) -> Dict[str, Any]:
    """Look up visitor history from database to accelerate return check-in."""
    if not phone and not visitor_name:
        return {"found": False, "message": "No identifier provided"}

    try:
        from database.connection import get_session_factory
        from database.models import Visitor
        import hashlib

        session = get_session_factory()()
        try:
            visitor = None
            if phone:
                normalized = "".join(ch for ch in phone if ch.isdigit())
                if len(normalized) >= 10:
                    phash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                    visitor = session.query(Visitor).filter(Visitor.phone_hash == phash).first()

            if not visitor and visitor_name:
                visitor = session.query(Visitor).filter(
                    Visitor.full_name.ilike(f"%{visitor_name.strip()}%")
                ).first()

            if visitor:
                return {
                    "found": True,
                    "visitor_id": visitor.id,
                    "visitor_code": visitor.visitor_code,
                    "full_name": visitor.full_name,
                    "company": visitor.company,
                    "category": visitor.category,
                    "consent_status": visitor.consent_status,
                }
        finally:
            session.close()
    except Exception as e:
        logger.warning("ADK lookup_visitor_history error: %s", e)

    return {"found": False}


def register_visitor_checkin_intent(
    name: str,
    purpose: str,
    company: Optional[str] = None,
    duration_minutes: int = 30,
    phone: Optional[str] = None
) -> Dict[str, Any]:
    """Validate visitor check-in intent, run duration bounds checks,
    and prepare entry record schema for the gate security system.
    """
    cleaned_name = (name or "").strip().title()
    dur_info = validate_and_format_duration(duration_minutes, purpose=purpose)
    
    return {
        "status": "APPROVED",
        "visitor_name": cleaned_name,
        "purpose": purpose or "Visitor",
        "company": company,
        "expected_duration_minutes": dur_info["approved_duration_minutes"],
        "formatted_duration_ta": dur_info["formatted_text_ta"],
        "formatted_duration_en": dur_info["formatted_text_en"],
        "phone": phone,
        "policy_note": dur_info["policy_note"],
    }


# ---------------------------------------------------------------------------
# Kiosk ADK Agent Definition
# ---------------------------------------------------------------------------

KIOSK_AGENT_INSTRUCTION = """You are the AI Gate Security Kiosk Agent for an apartment and community complex.
Your duty:
1. Greet visitors politely in Tamil or English.
2. Accurately identify their Name, Purpose (Delivery, Maintenance, Guest, Electrician, Plumber), and Expected Duration of stay.
3. If they represent a company (Swiggy, Zomato, Amazon, Porter, Zepto), classify Purpose as Delivery and extract Company.
4. Convert spoken time accurately: '1 hour' -> 60 minutes, '2 hours' -> 120 minutes, 'half an hour' -> 30 minutes.
5. If missing information (Name, Purpose, Duration), ask follow-up questions politely.
6. Once all information is gathered, execute register_visitor_checkin_intent and confirm check-in.
"""

class KioskADKAgent:
    """ADK Agent instance orchestrating gate kiosk conversational interactions."""

    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.model_name = model_name
        self.tools = [
            validate_and_format_duration,
            lookup_visitor_history,
            register_visitor_checkin_intent,
        ]
        self._native_agent = None
        if HAS_GOOGLE_ADK:
            try:
                self._native_agent = Agent(
                    model=self.model_name,
                    tools=self.tools,
                    instruction=KIOSK_AGENT_INSTRUCTION,
                )
                logger.info("Initialized Google ADK native agent: %s", model_name)
            except Exception as e:
                logger.warning("Failed initializing native google-adk Agent: %s", e)

    def process_turn(
        self,
        transcript: str,
        existing_data: Optional[Dict[str, Any]] = None,
        language: str = "ta-IN"
    ) -> Dict[str, Any]:
        """Process conversational turn using ADK tool-oriented workflow with fallback."""
        existing = existing_data or {}
        
        # 1. First run entity extraction
        from services.voice_agent_service import extract_visitor_details_from_speech
        extracted = extract_visitor_details_from_speech(transcript, language=language)

        # 2. Merge entities into existing state
        merged = dict(existing)
        if extracted.get("name") and not merged.get("name"):
            merged["name"] = extracted["name"]
        if extracted.get("company") and not merged.get("company"):
            merged["company"] = extracted["company"]
        if extracted.get("purpose") and extracted["purpose"] not in ("Visitor", "Other", None):
            merged["purpose"] = extracted["purpose"]
        elif merged.get("company") and (not merged.get("purpose") or merged.get("purpose") == "Visitor"):
            merged["purpose"] = "Delivery"

        turn_dur = extracted.get("expected_duration_minutes")
        if turn_dur:
            merged["expected_duration_minutes"] = turn_dur

        if extracted.get("phone") and not merged.get("phone"):
            merged["phone"] = extracted["phone"]

        # 3. Check for previous visitor history if phone or name is present
        history_match = None
        if merged.get("phone") or merged.get("name"):
            history_match = lookup_visitor_history(phone=merged.get("phone"), visitor_name=merged.get("name"))
            if history_match.get("found"):
                if not merged.get("name") and history_match.get("full_name"):
                    merged["name"] = history_match["full_name"]

        # 4. Check completeness & generate dialogue response
        has_name = bool(merged.get("name"))
        has_purpose = bool(merged.get("company") or (merged.get("purpose") and merged["purpose"] != "Visitor"))
        has_phone = bool(merged.get("phone") and len(str(merged["phone"])) >= 10)
        has_duration = bool(merged.get("expected_duration_minutes"))
        name_str = merged.get("name", "")

        # If returning visitor already found in DB, skip asking for phone
        if history_match and history_match.get("found"):
            has_phone = True

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
                reply_ta = f"சரி {name_str}! நீங்கள் எதற்காக வந்திருக்கிறீர்கள்? டெலிவரி, வேலை அல்லது விருந்தினரா? நிறுவனம் எது?"
                reply_en = f"Alright {name_str}! What is the purpose of your visit or which platform (e.g. Swiggy, Zomato)?"
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
            # Complete! Execute ADK checkin tool
            is_complete = True
            dur_check = validate_and_format_duration(
                merged.get("expected_duration_minutes", 30),
                purpose=merged.get("purpose", "Visitor")
            )
            merged["expected_duration_minutes"] = dur_check["approved_duration_minutes"]
            dur_ta = dur_check["formatted_text_ta"]
            reply_ta = f"சரி {name_str}! நீங்கள் இப்போது உள்ளே செல்ல அனுமதிக்கப்படுகிறீர்கள். உங்கள் வருகை {dur_ta} வரை பதிவு செய்யப்பட்டுவிட்டது!"
            reply_en = f"Alright {name_str}! You are permitted to enter. Your entry is registered for {dur_check['formatted_text_en']}!"


        return {
            "updated_data": merged,
            "is_complete": is_complete,
            "reply_tamil": reply_ta,
            "reply_english": reply_en,
            "raw_transcript": transcript,
            "history_match": history_match,
            "framework": "google-adk" if HAS_GOOGLE_ADK else "adk-compatible",
        }


# Singleton ADK agent instance
_kiosk_adk_agent: Optional[KioskADKAgent] = None

def get_kiosk_adk_agent() -> KioskADKAgent:
    global _kiosk_adk_agent
    if _kiosk_adk_agent is None:
        _kiosk_adk_agent = KioskADKAgent()
    return _kiosk_adk_agent

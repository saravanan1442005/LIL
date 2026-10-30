"""Tests for ADK Agent and Gemini Live API Voice Integration."""

import pytest
from services.kiosk_adk_agent import (
    validate_and_format_duration,
    lookup_visitor_history,
    register_visitor_checkin_intent,
    get_kiosk_adk_agent
)
from services.voice_agent_service import (
    conduct_visitor_conversation,
    get_gemini_live_session_config
)


def test_adk_duration_validation_tools():
    """Verify ADK tool calculates and bounds check-in stay duration."""
    # Delivery check
    deliv = validate_and_format_duration(60, purpose="Delivery")
    assert deliv["is_standard"] is False
    assert deliv["approved_duration_minutes"] == 60

    # Normal visitor check
    norm = validate_and_format_duration(120, purpose="Visitor")
    assert norm["is_standard"] is True
    assert norm["approved_duration_minutes"] == 120
    assert norm["formatted_text_ta"] == "2 மணி நேரம்"
    assert norm["formatted_text_en"] == "2 hour(s)"


def test_adk_register_intent():
    """Verify ADK intent registration tool produces compliant schema."""
    intent = register_visitor_checkin_intent(
        name="kavitha",
        purpose="Guest",
        company=None,
        duration_minutes=30,
        phone="9876543210"
    )
    assert intent["status"] == "APPROVED"
    assert intent["visitor_name"] == "Kavitha"
    assert intent["expected_duration_minutes"] == 30
    assert intent["phone"] == "9876543210"


def test_kiosk_adk_agent_multi_turn_flow():
    """Verify KioskADKAgent conducts turn-based dialogue and completeness evaluation."""
    agent = get_kiosk_adk_agent()
    
    # Turn 1: Only name spoken
    t1 = agent.process_turn("என் பெயர் செல்வம்", existing_data={})
    assert t1["is_complete"] is False
    assert t1["updated_data"].get("name") == "செல்வம்"

    # Turn 2: Purpose and duration spoken
    t2 = agent.process_turn("ஸ்விக்கி டெலிவரி 1 மணி நேரம்", existing_data=t1["updated_data"])
    assert t2["updated_data"]["name"] == "செல்வம்"
    assert t2["updated_data"]["company"] == "Swiggy"
    assert t2["updated_data"]["expected_duration_minutes"] == 60

    # Turn 3: Phone number provided completes the check-in
    t3 = agent.process_turn("என் எண் 9876543210", existing_data=t2["updated_data"])
    assert t3["is_complete"] is True
    assert t3["updated_data"]["phone"] == "9876543210"


def test_gemini_live_session_config():
    """Verify Gemini Multimodal Live API config builder returns expected WebSocket URL and setup payload."""
    config = get_gemini_live_session_config()
    assert "ws_url" in config
    assert "wss://generativelanguage.googleapis.com" in config["ws_url"]
    assert config["model"] == "models/gemini-2.0-flash-exp"
    assert "setup_message" in config
    assert "tools" in config["setup_message"]["setup"]
    
    # Verify function declaration inside tools
    tools = config["setup_message"]["setup"]["tools"]
    fn_names = [f["name"] for t in tools for f in t["functionDeclarations"]]
    assert "register_visitor" in fn_names

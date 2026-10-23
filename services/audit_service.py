"""Immutable audit logging service for DPDP Act 2023 compliance.
Logs all administrative operations, credential access, data searches, and un-blur requests.
"""
import logging
from typing import Optional, Dict, Any
from flask import request, g
from sqlalchemy.orm import Session
from database.models import AuditLog

logger = logging.getLogger("ecolifybuddy.audit")


def log_audit_event(
    session: Session,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    reason: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    role: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Record an immutable audit log entry."""
    # Attempt to extract identity from request context if not provided
    if not user_email:
        current_user = getattr(g, "current_user", None)
        if current_user:
            user_id = current_user.get("user_id")
            user_email = current_user.get("email", "anonymous")
            role = current_user.get("role", "Viewer")
        else:
            user_email = "system"
            role = "System"

    if not ip_address:
        try:
            ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
            if ip_address and "," in ip_address:
                ip_address = ip_address.split(",")[0].strip()
        except Exception:
            ip_address = "127.0.0.1"

    entry = AuditLog(
        user_id=user_id,
        user_email=user_email or "unknown",
        role=role or "Viewer",
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        reason=reason,
        details=details or {},
        ip_address=ip_address,
    )
    session.add(entry)
    session.commit()
    logger.info("AUDIT: [%s] User=%s (%s) Action=%s Target=%s/%s", 
                entry.timestamp.isoformat() if entry.timestamp else "",
                entry.user_email, entry.role, entry.action, entry.target_type, entry.target_id)
    return entry

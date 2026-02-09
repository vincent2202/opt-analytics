from ninja import Schema
from datetime import datetime
from typing import Optional
from decimal import Decimal
from uuid import UUID 
from typing import Any, Dict

# ============== ERROR SCHEMAS ==============

class ErrorSchema(Schema):
    detail: str

# ============== AUTH SCHEMAS ==============

class LoginSchema(Schema):
    username: str
    password: str


class TokenSchema(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # 1 hour in seconds


class RefreshSchema(Schema):
    refresh_token: str


# ============== TRACKING SCHEMAS ==============

class PageViewSchema(Schema):
    api_key: str
    session_id: str
    page_url: str
    page_title: Optional[str] = None
    page_path: Optional[str] = None
    referrer_url: Optional[str] = None
    user_agent: str
    ip_address: Optional[str] = None
    screen_resolution: Optional[str] = None
    language: Optional[str] = None
    
    # UTM parameters
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None


class EventSchema(Schema):
    api_key: str
    session_id: str
    event_type: str
    event_category: Optional[str] = None
    event_label: Optional[str] = None
    event_value: Optional[Decimal] = None
    
    element_id: Optional[str] = None
    element_class: Optional[str] = None
    element_text: Optional[str] = None
    element_tag: Optional[str] = None
    
    page_url: str
    page_path: Optional[str] = None
    time_since_page_load_ms: int
    time_since_session_start_seconds: int
    
    metadata: Optional[dict] = {}
    # ADD THIS FOR BOT DETECTION:
    time_spent_seconds: Optional[int] = None


# ============== ANALYTICS RESPONSE SCHEMAS ==============

class SessionOut(Schema):
    id: int
    session_id: UUID  # Change from str to UUID
    source: str
    device_type: str
    landing_page_url: str
    page_views_count: int
    events_count: int
    has_converted: bool
    created_at: datetime
    
    @staticmethod
    def resolve_session_id(obj):
        """Convert UUID to string for JSON serialization"""
        return str(obj.session_id)


class PageViewOut(Schema):
    id: int
    page_path: str
    page_title: Optional[str]
    sequence_number: int
    time_on_page_seconds: int
    viewed_at: datetime


class EventOut(Schema):
    id: int
    event_type: str
    event_category: Optional[str]
    event_label: Optional[str]
    element_text: Optional[str]
    occurred_at: datetime


class DashboardStats(Schema):
    total_sessions: int
    total_page_views: int
    total_events: int
    total_conversions: int
    avg_session_duration: int
    bounce_rate: float
    conversion_rate: float


# ============== EMAIL & DIAGNOSTIC SCHEMAS ==============

class CaptureEmailSchema(Schema):
    """Capture user email and optional contact info"""
    api_key: str
    session_id: str
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    # ADD THESE FOR BOT DETECTION:
    time_spent_seconds: Optional[int] = None
    honeypot_filled: Optional[bool] = False


class DiagnosticAnswersSchema(Schema):
    """Submit diagnostic/quiz answers"""
    api_key: str
    session_id: str
    diagnostic_name: str
    diagnostic_version: Optional[str] = None
    answers: Dict[str, Any]  # JSON object with all answers
    score: Optional[Decimal] = None
    result_category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    started_at: Optional[datetime] = None


class DiagnosticResponseOut(Schema):
    """Return diagnostic response"""
    id: int
    diagnostic_name: str
    result_category: Optional[str]
    score: Optional[Decimal]
    completed_at: datetime
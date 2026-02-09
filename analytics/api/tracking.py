# Keep all imports and helper function the same...
# Just update the router endpoint decorators:

from ninja import Router
from django.utils import timezone
from analytics.auth import APIKeyAuth
from analytics.schemas import PageViewSchema, EventSchema, ErrorSchema  # ADD ErrorSchema
from analytics.models import Session, PageView, Event, APIKey
from user_agents import parse
from urllib.parse import urlparse
import uuid

from analytics.schemas import (

    CaptureEmailSchema,  # ADD
    DiagnosticAnswersSchema,  # ADD
)
from analytics.models import (

    DiagnosticResponse,  # ADD
)

from analytics.services.bot_detector import update_session_bot_score

router = Router(tags=['Tracking'], auth=APIKeyAuth())


# Keep get_or_create_session function exactly the same...
def get_or_create_session(api_key: APIKey, session_id_str: str, request_data: dict, ip_address: str, user_agent_string: str):
    """Helper to get or create session"""
    
    try:
        session_uuid = uuid.UUID(session_id_str)
        session = Session.objects.get(session_id=session_uuid)
        
        # Update last activity
        session.last_activity_at = timezone.now()
        session.save(update_fields=['last_activity_at'])
        
        return session
        
    except (ValueError, Session.DoesNotExist):
        # Create new session
        user_agent = parse(user_agent_string)
        
        # Determine device type
        if user_agent.is_mobile:
            device_type = 'mobile'
        elif user_agent.is_tablet:
            device_type = 'tablet'
        elif user_agent.is_pc:
            device_type = 'desktop'
        else:
            device_type = 'unknown'
        
        # Parse referrer
        referrer_domain = None
        source = 'direct'
        if request_data.get('referrer_url'):
            parsed = urlparse(request_data['referrer_url'])
            referrer_domain = parsed.netloc
            
            # Determine source
            if 'google' in referrer_domain:
                source = 'organic'
            elif any(x in referrer_domain for x in ['facebook', 'twitter', 'linkedin', 'instagram']):
                source = 'social'
            elif referrer_domain:
                source = 'referral'
        
        if request_data.get('utm_source'):
            source = 'paid' if 'cpc' in request_data.get('utm_medium', '') else 'other'
        
        session = Session.objects.create(
            session_id=session_uuid if isinstance(session_uuid, uuid.UUID) else uuid.uuid4(),
            api_key=api_key,
            referrer_url=request_data.get('referrer_url'),
            referrer_domain=referrer_domain,
            source=source,
            utm_source=request_data.get('utm_source'),
            utm_medium=request_data.get('utm_medium'),
            utm_campaign=request_data.get('utm_campaign'),
            utm_term=request_data.get('utm_term'),
            utm_content=request_data.get('utm_content'),
            landing_page_url=request_data.get('page_url', ''),
            landing_page_title=request_data.get('page_title'),
            ip_address=ip_address,
            user_agent=user_agent_string,
            device_type=device_type,
            browser=user_agent.browser.family,
            browser_version=user_agent.browser.version_string,
            os=user_agent.os.family,
            os_version=user_agent.os.version_string,
            screen_resolution=request_data.get('screen_resolution'),
            language=request_data.get('language'),
        )
        
        return session


@router.post('/pageview', response={200: dict})  # Simple dict response
def track_pageview(request, payload: PageViewSchema):
    """
    Track a page view
    """
    # Get client IP
    ip_address = payload.ip_address or request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    # Get or create session
    session = get_or_create_session(
        api_key=request.api_key,
        session_id_str=payload.session_id,
        request_data=payload.dict(),
        ip_address=ip_address,
        user_agent_string=payload.user_agent
    )
    
    # Get sequence number
    last_page_view = session.page_views.order_by('-sequence_number').first()
    sequence_number = (last_page_view.sequence_number + 1) if last_page_view else 1
    
    # Update time on previous page
    if last_page_view and last_page_view.time_on_page_seconds == 0:
        time_diff = (timezone.now() - last_page_view.viewed_at).total_seconds()
        last_page_view.time_on_page_seconds = int(time_diff)
        last_page_view.save(update_fields=['time_on_page_seconds'])
    
    # Create page view
    page_view = PageView.objects.create(
        session=session,
        page_url=payload.page_url,
        page_title=payload.page_title,
        page_path=payload.page_path or urlparse(payload.page_url).path,
        sequence_number=sequence_number,
        previous_page_url=last_page_view.page_url if last_page_view else None,
    )
    
    # Update session metrics
    session.page_views_count = session.page_views.count()
    session.is_bounce = (session.page_views_count == 1)
    session.save(update_fields=['page_views_count', 'is_bounce'])
    
    return {'status': 'success', 'session_id': str(session.session_id)}


@router.post('/email', response={200: dict, 404: ErrorSchema})
def capture_email(request, payload: CaptureEmailSchema):
    """
    Capture user email and contact information
    Links email to existing session
    """
    try:
        session = Session.objects.get(session_id=payload.session_id)
    except Session.DoesNotExist:
        return 404, {'detail': 'Session not found'}
    
    # BOT DETECTION - Calculate score based on honeypot and timing
    bot_score = update_session_bot_score(
        session=session,
        time_spent=payload.time_spent_seconds,
        honeypot_filled=payload.honeypot_filled
    )
    
    # If high bot score, reject silently (don't tell bots they're detected)
    #if bot_score >= 70: 
    #    return {
    #        'status': 'success',
    #        'session_id': str(session.session_id),
    #        'email': payload.email,
    #        'bot_detected': True  # For debugging, remove in production
    #    }
    
    # Update session with user info
    session.email = payload.email
    if payload.name:
        session.name = payload.name
    if payload.company:
        session.company = payload.company
    if payload.phone:
        session.phone = payload.phone
    
    session.save(update_fields=['email', 'name', 'company', 'phone'])
    
    # Also link to CustomUser if exists
    from accounts.models import CustomUser
    try:
        user = CustomUser.objects.get(email=payload.email)
        session.user = user
        session.save(update_fields=['user'])
    except CustomUser.DoesNotExist:
        pass  # User doesn't exist yet, that's OK
    
    return {
        'status': 'success',
        'session_id': str(session.session_id),
        'email': session.email
    }


@router.post('/event', response={200: dict, 404: ErrorSchema})
def track_event(request, payload: EventSchema):
    """
    Track an event (CTA click, form submit, etc.)
    """
    try:
        session = Session.objects.get(session_id=payload.session_id)
    except Session.DoesNotExist:
        return 404, {'detail': 'Session not found'}
    
    # Update bot score if timing data provided
    if payload.time_spent_seconds is not None:
        update_session_bot_score(
            session=session,
            time_spent=payload.time_spent_seconds
        )
    
    # Get current page view if available
    page_view = session.page_views.filter(page_url=payload.page_url).order_by('-viewed_at').first()
    
    # Create event
    event = Event.objects.create(
        session=session,
        page_view=page_view,
        event_type=payload.event_type,
        event_category=payload.event_category,
        event_label=payload.event_label,
        event_value=payload.event_value,
        element_id=payload.element_id,
        element_class=payload.element_class,
        element_text=payload.element_text,
        element_tag=payload.element_tag,
        page_url=payload.page_url,
        page_path=payload.page_path or urlparse(payload.page_url).path,
        time_since_page_load_ms=payload.time_since_page_load_ms,
        time_since_session_start_seconds=payload.time_since_session_start_seconds,
        metadata=payload.metadata,
    )
    
    # Update session metrics
    session.events_count = session.events.count()
    
    # Check if conversion event
    if payload.event_type == 'conversion':
        session.has_converted = True
        session.conversion_event = payload.event_label
    
    session.save(update_fields=['events_count', 'has_converted', 'conversion_event'])
    
    return {'status': 'success', 'event_id': event.id}


@router.post('/diagnostic', response={200: dict, 404: ErrorSchema})
def submit_diagnostic(request, payload: DiagnosticAnswersSchema):
    """
    Submit diagnostic/quiz answers
    Stores answers as JSON and links to session
    """
    try:
        session = Session.objects.get(session_id=payload.session_id)
    except Session.DoesNotExist:
        return 404, {'detail': 'Session not found'}
    
    # Create diagnostic response
    diagnostic = DiagnosticResponse.objects.create(
        session=session,
        diagnostic_name=payload.diagnostic_name,
        diagnostic_version=payload.diagnostic_version,
        answers=payload.answers,
        score=payload.score,
        result_category=payload.result_category,
        metadata=payload.metadata,
        started_at=payload.started_at,
    )
    
    # Mark session as converted if this is a conversion event
    if not session.has_converted:
        session.has_converted = True
        session.conversion_event = f"diagnostic_{payload.diagnostic_name}"
        session.save(update_fields=['has_converted', 'conversion_event'])
    
    return {
        'status': 'success',
        'diagnostic_id': diagnostic.id,
        'session_id': str(session.session_id)
    }
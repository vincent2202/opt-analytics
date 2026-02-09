from ninja import Router
from typing import List
from django.db.models import Count, Avg, Sum, Q
from analytics.auth import JWTAuth
from analytics.schemas import SessionOut, DashboardStats
from analytics.models import Session, PageView, Event

from analytics.schemas import (

    DiagnosticResponseOut,  # ADD
)
from analytics.models import (

    DiagnosticResponse,  # ADD
)

router = Router(tags=['Analytics'], auth=JWTAuth())


@router.get('/dashboard', response=DashboardStats)
def get_dashboard_stats(request):
    """
    Get dashboard statistics (requires JWT authentication)
    """
    sessions = Session.objects.all()
    
    total_sessions = sessions.count()
    total_page_views = PageView.objects.count()
    total_events = Event.objects.count()
    total_conversions = sessions.filter(has_converted=True).count()
    
    avg_duration = sessions.aggregate(avg=Avg('duration_seconds'))['avg'] or 0
    bounce_rate = (sessions.filter(is_bounce=True).count() / total_sessions * 100) if total_sessions > 0 else 0
    conversion_rate = (total_conversions / total_sessions * 100) if total_sessions > 0 else 0
    
    return {
        'total_sessions': total_sessions,
        'total_page_views': total_page_views,
        'total_events': total_events,
        'total_conversions': total_conversions,
        'avg_session_duration': int(avg_duration),
        'bounce_rate': round(bounce_rate, 2),
        'conversion_rate': round(conversion_rate, 2),
    }


@router.get('/sessions', response=List[SessionOut])
def get_sessions(request, limit: int = 50, offset: int = 0):
    """
    Get recent sessions (requires JWT authentication)
    """
    sessions = Session.objects.select_related('api_key').order_by('-created_at')[offset:offset+limit]
    return sessions

@router.get('/diagnostics', response={200: dict}, auth=JWTAuth())
def get_diagnostic_analytics(request, diagnostic_name: str = None):
    """Get diagnostic completion funnel"""
    
    filters = {'event_type__startswith': 'diagnostic_'}
    if diagnostic_name:
        filters['event_label'] = diagnostic_name
    
    events = Event.objects.filter(**filters)
    
    # Funnel analysis
    funnel = {
        'started': events.filter(event_type='diagnostic_question_shown', metadata__step_number=1).count(),
        'completed_all_questions': events.filter(event_type='diagnostic_contact_form_shown').count(),
        'submitted_email': events.filter(event_type='diagnostic_email_submitted').count(),
        'skipped_email': events.filter(event_type='diagnostic_contact_skipped').count(),
        'viewed_results': events.filter(event_type='diagnostic_results_viewed').count(),
    }
    
    # Step-by-step dropoff
    steps = []
    for i in range(1, 10):  # Assuming max 10 questions
        step_shown = events.filter(
            event_type='diagnostic_question_shown',
            metadata__step_number=i
        ).count()
        
        step_completed = events.filter(
            event_type='diagnostic_step_completed',
            metadata__step_number=i
        ).count()
        
        if step_shown == 0:
            break
            
        steps.append({
            'step_number': i,
            'shown': step_shown,
            'completed': step_completed,
            'dropoff_rate': round((1 - step_completed / step_shown) * 100, 2) if step_shown > 0 else 0
        })
    
    return {
        'diagnostic_name': diagnostic_name,
        'funnel': funnel,
        'steps': steps,
        'conversion_rate': round(funnel['submitted_email'] / funnel['started'] * 100, 2) if funnel['started'] > 0 else 0
    }
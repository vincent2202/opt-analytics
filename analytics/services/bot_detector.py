# analytics/services/bot_detector.py
from analytics.models import Session


def calculate_bot_score(session: Session, time_spent: int = None, honeypot_filled: bool = False) -> int:
    """
    Calculate bot likelihood score (0-100)
    Higher score = more likely bot
    
    Args:
        session: Session object
        time_spent: Time spent on form/page in seconds
        honeypot_filled: Whether honeypot field was filled
    
    Returns:
        Bot score (0-100)
    """
    score = 0
    
    # 1. HONEYPOT FILLED - Major red flag
    if honeypot_filled:
        score += 60
    
    # 2. TIMING - Too fast (< 2 seconds for email form)
    if time_spent is not None and time_spent < 2:
        score += 40
    
    # 3. SUSPICIOUS USER AGENT
    ua = session.user_agent.lower()
    bot_keywords = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python', 'java']
    if any(keyword in ua for keyword in bot_keywords):
        score += 50
    
    # 4. TOO MANY PAGE VIEWS TOO FAST
    if session.page_views_count > 10:
        from django.utils import timezone
        time_elapsed = (timezone.now() - session.created_at).total_seconds()
        if time_elapsed < 60:  # 10+ pages in 1 minute
            score += 30
    
    # 5. NO EVENTS DESPITE MANY PAGE VIEWS
    if session.page_views_count > 5 and session.events_count == 0:
        score += 15
    
    # 6. EMPTY REFERRER (direct visit, could be bot)
    if not session.referrer_url and session.source == 'direct':
        score += 10
    
    return min(score, 100)  # Cap at 100


def update_session_bot_score(session: Session, time_spent: int = None, honeypot_filled: bool = False):
    """
    Update session with bot detection score
    """
    score = calculate_bot_score(session, time_spent, honeypot_filled)
    
    session.bot_score = score
    session.is_suspected_bot = (score >= 50)  # Threshold: 50+
    session.save(update_fields=['bot_score', 'is_suspected_bot'])
    
    return score
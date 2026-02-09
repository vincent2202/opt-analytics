from django.db import models
from django.contrib.postgres.indexes import BrinIndex
from accounts.models import CustomUser
import uuid


class APIKey(models.Model):
    """API keys for authenticating tracking requests from different domains"""
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255, help_text="e.g., 'Main Website', 'Landing Page'")
    domain = models.CharField(max_length=255, help_text="Expected origin domain")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analytics_api_keys'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
    
    def __str__(self):
        return f"{self.name} ({self.domain})"


class Session(models.Model):
    """Visitor session - groups all activity from one visit"""
    SESSION_SOURCE_CHOICES = [
        ('organic', 'Organic Search'),
        ('paid', 'Paid Search'),
        ('social', 'Social Media'),
        ('referral', 'Referral'),
        ('direct', 'Direct'),
        ('email', 'Email'),
        ('other', 'Other'),
    ]
    
    DEVICE_CHOICES = [
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('unknown', 'Unknown'),
    ]
    
    # Primary identification
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='analytics_sessions',
                            help_text="Linked when user logs in/registers")
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name='sessions')
    
    # Traffic source & referrer (Layer 1: where they came from)
    referrer_url = models.URLField(max_length=2048, blank=True, null=True)
    referrer_domain = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    source = models.CharField(max_length=20, choices=SESSION_SOURCE_CHOICES, default='direct', db_index=True)
    
    # UTM parameters
    utm_source = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    utm_medium = models.CharField(max_length=255, blank=True, null=True)
    utm_campaign = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    utm_term = models.CharField(max_length=255, blank=True, null=True)
    utm_content = models.CharField(max_length=255, blank=True, null=True)
    search_keywords = models.CharField(max_length=500, blank=True, null=True)
    
    # Entry point (Layer 2: landing page)
    landing_page_url = models.CharField(max_length=2048, db_index=True)
    landing_page_title = models.CharField(max_length=500, blank=True, null=True)
    
    # Technical details
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, default='unknown', db_index=True)
    browser = models.CharField(max_length=100, blank=True, null=True)
    browser_version = models.CharField(max_length=50, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True)
    os_version = models.CharField(max_length=50, blank=True, null=True)
    screen_resolution = models.CharField(max_length=20, blank=True, null=True)
    language = models.CharField(max_length=10, blank=True, null=True)
    
    # Geography (optional, can be derived from IP)
    country = models.CharField(max_length=2, blank=True, null=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Session metrics
    page_views_count = models.IntegerField(default=0)
    events_count = models.IntegerField(default=0)
    duration_seconds = models.IntegerField(default=0, help_text="Total session duration")
    is_bounce = models.BooleanField(default=False, help_text="Only viewed one page")
    
    # Conversion tracking
    has_converted = models.BooleanField(default=False, db_index=True)
    conversion_event = models.CharField(max_length=100, blank=True, null=True)

    # User identification (add these NEW fields before timestamps section)
    email = models.EmailField(blank=True, null=True, db_index=True, 
                             help_text="User email when captured")
    name = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)

    # Bot detection (add before timestamps section)
    is_suspected_bot = models.BooleanField(default=False, db_index=True,
                                          help_text="Flagged as potential bot")
    bot_score = models.IntegerField(default=0,
                                   help_text="Bot likelihood score (0-100)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'analytics_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at', 'source']),
            models.Index(fields=['api_key', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Session {self.session_id} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class PageView(models.Model):
    """Individual page view within a session (Layer 3: visitor pathway)"""
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='page_views')
    
    # Page details
    page_url = models.CharField(max_length=2048, db_index=True)
    page_title = models.CharField(max_length=500, blank=True, null=True)
    page_path = models.CharField(max_length=1024, blank=True, null=True, db_index=True)
    
    # Navigation tracking
    sequence_number = models.IntegerField(help_text="Order in session: 1st, 2nd, 3rd page viewed")
    previous_page_url = models.CharField(max_length=2048, blank=True, null=True)
    
    # Engagement metrics
    time_on_page_seconds = models.IntegerField(default=0, help_text="Calculated from next page view")
    scroll_depth_percent = models.IntegerField(default=0, help_text="Max scroll percentage")
    
    # Timestamps
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'analytics_page_views'
        ordering = ['session', 'sequence_number']
        indexes = [
            models.Index(fields=['session', 'sequence_number']),
            models.Index(fields=['page_path', 'viewed_at']),
            models.Index(fields=['viewed_at']),
        ]
    
    def __str__(self):
        return f"{self.session.session_id} - Page {self.sequence_number}: {self.page_path}"


class Event(models.Model):
    """User interactions: clicks, form submits, etc. (Layer 4: CTA tracking)"""
    
    EVENT_TYPE_CHOICES = [
        ('cta_click', 'CTA Click'),
        ('button_click', 'Button Click'),
        ('link_click', 'Link Click'),
        ('form_submit', 'Form Submit'),
        ('form_start', 'Form Started'),
        ('download', 'Download'),
        ('video_play', 'Video Play'),
        ('video_complete', 'Video Complete'),
        ('scroll', 'Scroll Event'),
        ('outbound_click', 'Outbound Link Click'),
        ('search', 'Site Search'),
        ('conversion', 'Conversion'),
        ('custom', 'Custom Event'),
        # Diagnostic-specific events
        ('diagnostic_started', 'Diagnostic Started'),
        ('diagnostic_question_shown', 'Diagnostic Question Shown'),
        ('diagnostic_step_completed', 'Diagnostic Step Completed'),
        ('diagnostic_contact_form_shown', 'Diagnostic Contact Form Shown'),
        ('diagnostic_email_submitted', 'Diagnostic Email Submitted'),
        ('diagnostic_contact_skipped', 'Diagnostic Contact Skipped'),
        ('diagnostic_results_viewed', 'Diagnostic Results Viewed'),
        ('diagnostic_restarted', 'Diagnostic Restarted'),
        ('diagnostic_abandoned', 'Diagnostic Abandoned'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='events')
    page_view = models.ForeignKey(PageView, on_delete=models.CASCADE, related_name='events', 
                                  null=True, blank=True)
    
    # Event details
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, db_index=True)
    event_category = models.CharField(max_length=100, blank=True, null=True, db_index=True,
                                     help_text="e.g., 'Header CTA', 'Footer CTA', 'Pricing'")
    event_label = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="e.g., 'Download Brochure', 'Contact Sales'")
    event_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Optional numeric value (e.g., order amount)")
    
    # Element details
    element_id = models.CharField(max_length=255, blank=True, null=True)
    element_class = models.CharField(max_length=255, blank=True, null=True)
    element_text = models.CharField(max_length=500, blank=True, null=True)
    element_tag = models.CharField(max_length=50, blank=True, null=True)
    
    # Page context
    page_url = models.CharField(max_length=2048)
    page_path = models.CharField(max_length=1024, blank=True, null=True)
    
    # Timing (how long before they clicked)
    time_since_page_load_ms = models.IntegerField(help_text="Milliseconds since page loaded")
    time_since_session_start_seconds = models.IntegerField(help_text="Seconds since session started")
    
    # Additional metadata (JSON for flexibility)
    metadata = models.JSONField(default=dict, blank=True, 
                               help_text="Additional event-specific data")
    
    # Timestamp
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'analytics_events'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['session', 'occurred_at']),
            models.Index(fields=['event_type', 'occurred_at']),
            models.Index(fields=['event_category', 'occurred_at']),
            models.Index(fields=['page_path', 'event_type']),
        ]
    
    def __str__(self):
        return f"{self.event_type}: {self.element_text or self.event_label} at {self.occurred_at}"


class DailyMetric(models.Model):
    """Aggregated daily statistics for fast reporting"""
    
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name='daily_metrics')
    date = models.DateField(db_index=True)
    
    # Traffic metrics
    sessions_count = models.IntegerField(default=0)
    unique_users_count = models.IntegerField(default=0)
    page_views_count = models.IntegerField(default=0)
    events_count = models.IntegerField(default=0)
    
    # Engagement
    avg_session_duration_seconds = models.IntegerField(default=0)
    avg_pages_per_session = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bounce_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Conversions
    conversions_count = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Traffic sources breakdown (JSON for flexibility)
    sources_breakdown = models.JSONField(default=dict, blank=True)
    devices_breakdown = models.JSONField(default=dict, blank=True)
    top_pages = models.JSONField(default=dict, blank=True)
    top_landing_pages = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_daily_metrics'
        unique_together = [['api_key', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['api_key', 'date']),
        ]
    
    def __str__(self):
        return f"{self.api_key.name} - {self.date}"
    
class DiagnosticResponse(models.Model):
    """Store diagnostic/quiz answers as JSON"""
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='diagnostics')
    
    # Diagnostic metadata
    diagnostic_name = models.CharField(max_length=255, help_text="Name of the diagnostic/quiz")
    diagnostic_version = models.CharField(max_length=50, blank=True, null=True, 
                                         help_text="Version if you iterate on questions")
    
    # Answers stored as JSON
    answers = models.JSONField(help_text="All answers as JSON object")
    
    # Computed results/scores (optional)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                help_text="Calculated score if applicable")
    result_category = models.CharField(max_length=100, blank=True, null=True,
                                      help_text="e.g., 'Beginner', 'Advanced', 'High Risk'")
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True,
                               help_text="Any extra data (time spent, partial completion, etc.)")
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True, 
                                     help_text="When user started diagnostic")
    completed_at = models.DateTimeField(auto_now_add=True, 
                                       help_text="When user completed diagnostic")
    
    class Meta:
        db_table = 'analytics_diagnostic_responses'
        ordering = ['-completed_at']
        indexes = [
            models.Index(fields=['session', 'completed_at']),
            models.Index(fields=['diagnostic_name', 'completed_at']),
        ]
    
    def __str__(self):
        return f"{self.diagnostic_name} - {self.session.session_id}"
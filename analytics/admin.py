from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import APIKey, Session, PageView, Event, DailyMetric, DiagnosticResponse


# Resources define which fields to import/export
class APIKeyResource(resources.ModelResource):
    class Meta:
        model = APIKey
        fields = ('id', 'key', 'name', 'domain', 'is_active', 'created_at')
        export_order = ('id', 'name', 'domain', 'key', 'is_active', 'created_at')


class SessionResource(resources.ModelResource):
    class Meta:
        model = Session
        fields = (
            'id', 'session_id', 'user__email', 'api_key__name',
            'source', 'referrer_domain', 'utm_source', 'utm_campaign',
            'landing_page_url', 'device_type', 'browser', 'country',
            'page_views_count', 'events_count', 'has_converted', 'created_at'
        )
        export_order = fields


class PageViewResource(resources.ModelResource):
    class Meta:
        model = PageView
        fields = (
            'id', 'session__session_id', 'page_url', 'page_title', 'page_path',
            'sequence_number', 'time_on_page_seconds', 'scroll_depth_percent', 'viewed_at'
        )
        export_order = fields


class EventResource(resources.ModelResource):
    class Meta:
        model = Event
        fields = (
            'id', 'session__session_id', 'event_type', 'event_category', 'event_label',
            'element_id', 'element_text', 'page_url', 'time_since_page_load_ms',
            'time_since_session_start_seconds', 'occurred_at'
        )
        export_order = fields


class DailyMetricResource(resources.ModelResource):
    class Meta:
        model = DailyMetric
        fields = (
            'id', 'api_key__name', 'date', 'sessions_count', 'unique_users_count',
            'page_views_count', 'events_count', 'avg_session_duration_seconds',
            'avg_pages_per_session', 'bounce_rate', 'conversions_count', 'conversion_rate'
        )
        export_order = fields


# Admin classes with Import/Export
@admin.register(APIKey)
class APIKeyAdmin(ImportExportModelAdmin):
    resource_class = APIKeyResource
    list_display = ['name', 'domain', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'domain', 'key']


@admin.register(Session)
class SessionAdmin(ImportExportModelAdmin):
    resource_class = SessionResource
    list_display = ['session_id', 'user', 'source', 'device_type', 'page_views_count', 'created_at']
    list_filter = ['source', 'device_type', 'has_converted', 'created_at']
    search_fields = ['session_id', 'ip_address', 'landing_page_url']
    readonly_fields = ['session_id', 'created_at', 'last_activity_at']
    
    # Limit export to prevent memory issues
    def get_export_queryset(self, request):
        """Limit export to last 30 days by default"""
        qs = super().get_export_queryset(request)
        from django.utils import timezone
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return qs.filter(created_at__gte=thirty_days_ago)


@admin.register(PageView)
class PageViewAdmin(ImportExportModelAdmin):
    resource_class = PageViewResource
    list_display = ['session', 'sequence_number', 'page_path', 'time_on_page_seconds', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['page_url', 'page_title', 'session__session_id']
    readonly_fields = ['viewed_at']
    
    def get_export_queryset(self, request):
        """Limit export to last 30 days by default"""
        qs = super().get_export_queryset(request)
        from django.utils import timezone
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return qs.filter(viewed_at__gte=thirty_days_ago)


@admin.register(Event)
class EventAdmin(ImportExportModelAdmin):
    list_display = [
        'id',
        'event_type',
        'event_category', 
        'event_label',
        'session',
        'page_path',
        'occurred_at',  # Changed from created_at
    ]
    list_filter = [
        'event_type',
        'event_category',
        'occurred_at',  # Changed from created_at
    ]
    search_fields = [
        'event_type',
        'event_label',
        'session__session_id',
        'session__email',
        'element_text',
    ]
    readonly_fields = ['metadata_display', 'occurred_at']  # Changed from created_at
    
    fieldsets = (
        ('Event Info', {
            'fields': ('event_type', 'event_category', 'event_label', 'event_value')
        }),
        ('Session', {
            'fields': ('session', 'page_view')
        }),
        ('Element Details', {
            'fields': ('element_id', 'element_class', 'element_text', 'element_tag'),
            'classes': ('collapse',)
        }),
        ('Page Context', {
            'fields': ('page_url', 'page_path')
        }),
        ('Timing', {
            'fields': ('time_since_page_load_ms', 'time_since_session_start_seconds')
        }),
        ('Additional Data', {
            'fields': ('metadata_display',)
        }),
        ('Timestamps', {
            'fields': ('occurred_at',)  # Changed from created_at
        }),
    )
    
    def metadata_display(self, obj):
        """Display metadata as formatted JSON"""
        import json
        return json.dumps(obj.metadata, indent=2, ensure_ascii=False)
    metadata_display.short_description = 'Metadata (JSON)'
    
    def get_queryset(self, request):
        """Limit exports to last 30 days by default"""
        qs = super().get_queryset(request)
        if not request.GET.get('all'):
            from django.utils import timezone
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            qs = qs.filter(occurred_at__gte=thirty_days_ago)  # Changed from created_at
        return qs
    


class DiagnosticResponseResource(resources.ModelResource):
    class Meta:
        model = DiagnosticResponse
        fields = (
            'id', 'session__session_id', 'session__email', 'diagnostic_name',
            'diagnostic_version', 'score', 'result_category', 'started_at', 'completed_at'
        )
        export_order = fields


@admin.register(DiagnosticResponse)
class DiagnosticResponseAdmin(ImportExportModelAdmin):
    resource_class = DiagnosticResponseResource
    list_display = [
        'id',
        'diagnostic_name',
        'session',
        'result_category',
        'score',
        'completed_at',
    ]
    list_filter = [
        'diagnostic_name',
        'result_category',
        'completed_at',
    ]
    search_fields = [
        'diagnostic_name',
        'session__session_id',
        'session__email',
        'result_category',
    ]
    readonly_fields = ['answers_display', 'metadata_display', 'started_at', 'completed_at']
    
    fieldsets = (
        ('Diagnostic Info', {
            'fields': ('diagnostic_name', 'diagnostic_version', 'score', 'result_category')
        }),
        ('Session', {
            'fields': ('session',)
        }),
        ('Answers', {
            'fields': ('answers_display',)
        }),
        ('Additional Data', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at')
        }),
    )
    
    def answers_display(self, obj):
        """Display answers as formatted JSON"""
        import json
        return json.dumps(obj.answers, indent=2, ensure_ascii=False)
    answers_display.short_description = 'Answers (JSON)'
    
    def metadata_display(self, obj):
        """Display metadata as formatted JSON"""
        import json
        return json.dumps(obj.metadata, indent=2, ensure_ascii=False)
    metadata_display.short_description = 'Metadata (JSON)'
    
    def get_queryset(self, request):
        """Limit exports to last 30 days by default"""
        qs = super().get_queryset(request)
        if not request.GET.get('all'):
            from django.utils import timezone
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            qs = qs.filter(completed_at__gte=thirty_days_ago)
        return qs
from ninja import NinjaAPI
from analytics.api.auth import router as auth_router
from analytics.api.tracking import router as tracking_router
from analytics.api.analytics import router as analytics_router

api = NinjaAPI(
    title="Analytics API",
    version="1.0.0",
    description="Analytics tracking and reporting API"
)

# Add routers
api.add_router('/auth', auth_router)
api.add_router('/track', tracking_router)
api.add_router('/analytics', analytics_router)
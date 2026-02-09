from ninja.security import HttpBearer
from django.http import HttpRequest
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from accounts.models import CustomUser
from analytics.models import APIKey


class JWTAuth(HttpBearer):
    """JWT Authentication for protected analytics endpoints"""
    
    def authenticate(self, request: HttpRequest, token: str):
        try:
            # Validate JWT token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            # Get user
            user = CustomUser.objects.get(id=user_id)
            
            # Attach user to request
            request.user = user
            return user
            
        except (InvalidToken, TokenError, CustomUser.DoesNotExist):
            return None


class APIKeyAuth:
    """API Key Authentication for public tracking endpoints"""
    
    def __call__(self, request: HttpRequest):
        # Try to get API key from header first
        api_key = request.headers.get('X-Analytics-Key')
        
        # If not in header, try from request body
        if not api_key and hasattr(request, 'data'):
            api_key = request.data.get('api_key')
        
        if not api_key:
            return None
        
        # Validate API key
        try:
            api_key_obj = APIKey.objects.get(key=api_key, is_active=True)
            request.api_key = api_key_obj
            return api_key_obj
        except APIKey.DoesNotExist:
            return None
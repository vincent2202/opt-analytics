from ninja import Router
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from analytics.schemas import LoginSchema, TokenSchema, RefreshSchema, ErrorSchema

router = Router(tags=['Authentication'])


@router.post('/login', response={200: TokenSchema, 401: ErrorSchema, 403: ErrorSchema})
def login(request, payload: LoginSchema):
    """
    Login endpoint for admin users to get JWT tokens
    """
    user = authenticate(username=payload.username, password=payload.password)
    
    if user is None:
        return 401, {'detail': 'Invalid credentials'}
    
    if not user.is_active:
        return 403, {'detail': 'User account is disabled'}
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    return 200, {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'token_type': 'bearer',
        'expires_in': 3600,  # 1 hour
    }


@router.post('/refresh', response={200: TokenSchema, 401: ErrorSchema})
def refresh_token(request, payload: RefreshSchema):
    """
    Refresh access token using refresh token
    """
    try:
        refresh = RefreshToken(payload.refresh_token)
        
        return 200, {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'token_type': 'bearer',
            'expires_in': 3600,
        }
    except Exception as e:
        return 401, {'detail': 'Invalid or expired refresh token'}
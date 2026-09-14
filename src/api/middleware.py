"""
API middleware for authentication and security.
"""

from functools import wraps
from typing import Callable


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for API endpoints.
    
    Usage:
        @require_auth
        def protected_endpoint():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check for authentication token
        # This is a placeholder - actual implementation would check
        # JWT tokens, API keys, etc.
        
        # For now, just pass through
        # In production, this would validate credentials
        return func(*args, **kwargs)
    
    return wrapper


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    Decorator to apply rate limiting to API endpoints.
    
    Usage:
        @rate_limit(max_requests=100, window_seconds=60)
        def limited_endpoint():
            ...
    """
    from .rate_limiter import RateLimiter
    
    limiter = RateLimiter(max_requests, window_seconds)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get user ID from request context
            # For now, use a default
            user_id = "default_user"
            
            if not limiter.check_rate_limit(user_id):
                raise Exception("Rate limit exceeded")
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

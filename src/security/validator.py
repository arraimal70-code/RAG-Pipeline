"""
Security validation and sanitization for RAG Pipeline.

Provides:
- Document validation
- Query validation
- Input sanitization
- Rate limiting
- Path traversal prevention
"""

import re
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import time
from collections import defaultdict


class DocumentValidator:
    """Validates documents for security and integrity."""
    
    def __init__(self, max_size_mb: int = 50, allowed_extensions: list = None):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions or ['.pdf', '.txt', '.md']
        
        # Patterns for malicious content
        self.malicious_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),  # onclick, onload, etc.
            re.compile(r'eval\s*\(', re.IGNORECASE),
            re.compile(r'exec\s*\(', re.IGNORECASE),
        ]
    
    def validate(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate a document file.
        
        Returns:
            (is_valid, reason)
        """
        # Check file exists
        if not file_path.exists():
            return False, "File does not exist"
        
        # Check extension
        if file_path.suffix.lower() not in self.allowed_extensions:
            return False, f"File extension {file_path.suffix} not allowed"
        
        # Check size
        file_size = file_path.stat().st_size
        if file_size > self.max_size_bytes:
            return False, f"File size {file_size} exceeds maximum {self.max_size_bytes}"
        
        # Check filename for malicious patterns
        filename = file_path.name
        if not self._is_safe_filename(filename):
            return False, "Filename contains malicious patterns"
        
        # Check path for traversal
        if not self._is_safe_path(file_path):
            return False, "Path contains traversal attempts"
        
        return True, "Valid"
    
    def validate_path(self, path_str: str) -> Tuple[bool, str]:
        """Validate a path string for safety."""
        # Check for path traversal
        if '..' in path_str:
            return False, "Path contains '..' traversal"
        
        # Check for absolute paths (unless explicitly allowed)
        path = Path(path_str)
        if path.is_absolute():
            # Could be allowed in some contexts, but flag it
            return False, "Absolute paths not allowed"
        
        return True, "Valid"
    
    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize document metadata."""
        sanitized = {}
        
        for key, value in metadata.items():
            if isinstance(value, str):
                # Remove potentially dangerous content
                sanitized_value = self._sanitize_string(value)
                sanitized[key] = sanitized_value
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe."""
        # Check for null bytes
        if '\x00' in filename:
            return False
        
        # Check for path separators
        if '/' in filename or '\\' in filename:
            return False
        
        # Check for special characters that could be used in attacks
        dangerous_chars = ['<', '>', '"', "'", ';', '&', '|', '`', '$', '(', ')', '{', '}']
        for char in dangerous_chars:
            if char in filename:
                return False
        
        return True
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is safe (no traversal)."""
        try:
            # Resolve to absolute path
            resolved = path.resolve()
            
            # Check if it's within allowed directories
            # For now, just check it doesn't escape to system directories
            dangerous_dirs = ['/etc', '/proc', '/sys', '/dev', '/var', 'C:\\Windows']
            
            resolved_str = str(resolved)
            for dangerous in dangerous_dirs:
                if resolved_str.startswith(dangerous):
                    return False
            
            return True
        except (OSError, ValueError):
            return False
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize a string by removing dangerous patterns."""
        # Remove script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove event handlers
        text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
        
        # Remove javascript: URLs
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        # Remove SQL injection patterns
        text = re.sub(r'(\b(or|and)\b\s+\d+\s*=\s*\d+)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(\b(drop|delete|insert|update)\b\s+table)', '', text, flags=re.IGNORECASE)
        
        # Remove template injection patterns
        text = re.sub(r'\{\{.*?\}\}', '', text)
        text = re.sub(r'\$\{.*?\}', '', text)
        
        return text


class QueryValidator:
    """Validates queries for security and safety."""
    
    def __init__(self, max_length: int = 10000):
        self.max_length = max_length
        
        # Injection patterns
        self.injection_patterns = [
            re.compile(r'ignore\s+(all\s+)?previous\s+instructions', re.IGNORECASE),
            re.compile(r'ignore\s+(all\s+)?above\s+instructions', re.IGNORECASE),
            re.compile(r'disregard\s+(all\s+)?previous', re.IGNORECASE),
            re.compile(r'forget\s+(all\s+)?(your\s+)?(instructions|constraints)', re.IGNORECASE),
            re.compile(r'you\s+are\s+now\s+in\s+debug\s+mode', re.IGNORECASE),
            re.compile(r'system\s*:\s*override', re.IGNORECASE),
            re.compile(r'new\s+instructions\s*:', re.IGNORECASE),
            re.compile(r'reveal\s+(your\s+)?system\s+prompt', re.IGNORECASE),
            re.compile(r'output\s+(your\s+)?(internal\s+)?state', re.IGNORECASE),
        ]
    
    def validate(self, query: str) -> Tuple[bool, str]:
        """
        Validate a query.
        
        Returns:
            (is_safe, reason)
        """
        # Check length
        if len(query) > self.max_length:
            return False, f"Query exceeds maximum length of {self.max_length}"
        
        # Check for injection patterns
        for pattern in self.injection_patterns:
            if pattern.search(query):
                return False, f"Query contains potential injection pattern: {pattern.pattern}"
        
        # Check for null bytes
        if '\x00' in query:
            return False, "Query contains null bytes"
        
        return True, "Valid"
    
    def sanitize(self, query: str) -> str:
        """Sanitize a query by removing dangerous patterns."""
        # Remove injection patterns
        for pattern in self.injection_patterns:
            query = pattern.sub('', query)
        
        # Remove null bytes
        query = query.replace('\x00', '')
        
        # Strip whitespace
        query = query.strip()
        
        return query


class RateLimiter:
    """Rate limiting for API requests."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if a user has exceeded rate limit.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        
        # Remove old requests outside window
        self.requests[user_id] = [
            t for t in self.requests[user_id]
            if current_time - t < self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Record request
        self.requests[user_id].append(current_time)
        
        return True
    
    def get_remaining(self, user_id: str) -> int:
        """Get remaining requests for a user."""
        current_time = time.time()
        
        # Clean old requests
        self.requests[user_id] = [
            t for t in self.requests[user_id]
            if current_time - t < self.window_seconds
        ]
        
        return max(0, self.max_requests - len(self.requests[user_id]))
    
    def get_reset_time(self, user_id: str) -> Optional[float]:
        """Get time until rate limit resets."""
        if not self.requests[user_id]:
            return None
        
        oldest_request = min(self.requests[user_id])
        reset_time = oldest_request + self.window_seconds
        
        return max(0, reset_time - time.time())


def sanitize_input(text: str) -> str:
    """General input sanitization."""
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove control characters (except newline, tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Remove common injection patterns
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    return text

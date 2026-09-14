"""
Enhanced security layer with comprehensive protection against attacks.
"""

import re
import logging
import hashlib
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Base exception for security violations."""
    pass


class PromptInjectionError(SecurityError):
    """Raised when prompt injection is detected."""
    pass


class DocumentValidationError(SecurityError):
    """Raised when document validation fails."""
    pass


class RateLimitError(SecurityError):
    """Raised when rate limit is exceeded."""
    pass


class DocumentValidator:
    """
    Comprehensive document validation and sanitization.
    
    Protects against:
    - Malicious file types
    - Oversized documents
    - Path traversal attacks
    - Malicious metadata
    - Corrupted files
    """
    
    def __init__(
        self,
        max_size_mb: int = 50,
        max_pages: int = 500,
        allowed_extensions: Optional[List[str]] = None,
    ):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_pages = max_pages
        self.allowed_extensions = allowed_extensions or ['.pdf', '.txt', '.md']
        
        # Malicious patterns in filenames
        self.malicious_filename_patterns = [
            re.compile(r'\.\./'),  # Path traversal
            re.compile(r'\.\.\\'),  # Windows path traversal
            re.compile(r'[<>:"|?*\x00-\x1f]'),  # Invalid characters
            re.compile(r'\.(exe|bat|cmd|sh|ps1|js|vbs)$', re.IGNORECASE),  # Executable extensions
        ]
        
        # Malicious metadata patterns
        self.malicious_metadata_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers
            re.compile(r'eval\s*\(', re.IGNORECASE),
            re.compile(r'exec\s*\(', re.IGNORECASE),
            re.compile(r'\{\{.*?\}\}'),  # Template injection
            re.compile(r'\$\{.*?\}'),  # Expression injection
        ]
        
        logger.info(f"DocumentValidator initialized (max_size={max_size_mb}MB, max_pages={max_pages})")
    
    def validate(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate a document file.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Check file exists
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check file is readable
            if not file_path.is_file():
                return False, "Path is not a file"
            
            # Check extension
            if file_path.suffix.lower() not in self.allowed_extensions:
                return False, f"File extension {file_path.suffix} not allowed"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_size_bytes:
                return False, f"File size {file_size} bytes exceeds maximum {self.max_size_bytes} bytes"
            
            if file_size == 0:
                return False, "File is empty"
            
            # Check filename for malicious patterns
            filename = file_path.name
            if not self._is_safe_filename(filename):
                return False, "Filename contains malicious patterns"
            
            # Check for path traversal
            if not self._is_safe_path(file_path):
                return False, "Path contains traversal attempts"
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and not self._is_safe_mime_type(mime_type):
                return False, f"MIME type {mime_type} not allowed"
            
            return True, "Valid"
            
        except Exception as e:
            logger.error(f"Document validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def validate_path(self, path_str: str) -> Tuple[bool, str]:
        """Validate a path string for safety."""
        try:
            path = Path(path_str)
            
            # Check for path traversal
            if '..' in path.parts:
                return False, "Path contains '..' traversal"
            
            # Check for absolute paths
            if path.is_absolute():
                return False, "Absolute paths not allowed"
            
            # Check for null bytes
            if '\x00' in path_str:
                return False, "Path contains null bytes"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Path validation error: {str(e)}"
    
    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize document metadata."""
        sanitized = {}
        
        for key, value in metadata.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_metadata(value)
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
        
        # Check for malicious patterns
        for pattern in self.malicious_filename_patterns:
            if pattern.search(filename):
                return False
        
        return True
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is safe (no traversal)."""
        try:
            # Resolve to absolute path
            resolved = path.resolve()
            
            # Check if it's within allowed directories
            dangerous_dirs = ['/etc', '/proc', '/sys', '/dev', '/var', 'C:\\Windows']
            
            resolved_str = str(resolved)
            for dangerous in dangerous_dirs:
                if resolved_str.startswith(dangerous):
                    return False
            
            return True
        except (OSError, ValueError):
            return False
    
    def _is_safe_mime_type(self, mime_type: str) -> bool:
        """Check if MIME type is safe."""
        allowed_types = [
            'application/pdf',
            'text/plain',
            'text/markdown',
        ]
        return mime_type in allowed_types
    
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
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        return text


class QueryValidator:
    """
    Query validation and sanitization.
    
    Protects against:
    - Prompt injection attacks
    - Oversized queries
    - Malicious content
    """
    
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
            re.compile(r'act\s+as\s+if\s+you\s+have\s+no\s+restrictions', re.IGNORECASE),
            re.compile(r'bypass\s+(all\s+)?(safety|security|filters)', re.IGNORECASE),
        ]
        
        logger.info(f"QueryValidator initialized (max_length={max_length})")
    
    def validate(self, query: str) -> Tuple[bool, str]:
        """
        Validate a query.
        
        Returns:
            Tuple of (is_safe, reason)
        """
        try:
            # Check length
            if len(query) > self.max_length:
                return False, f"Query exceeds maximum length of {self.max_length}"
            
            if len(query.strip()) == 0:
                return False, "Query is empty"
            
            # Check for injection patterns
            for pattern in self.injection_patterns:
                if pattern.search(query):
                    return False, f"Query contains potential injection pattern: {pattern.pattern}"
            
            # Check for null bytes
            if '\x00' in query:
                return False, "Query contains null bytes"
            
            # Check for control characters (except newline, tab)
            if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', query):
                return False, "Query contains control characters"
            
            return True, "Valid"
            
        except Exception as e:
            logger.error(f"Query validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def sanitize(self, query: str) -> str:
        """Sanitize a query by removing dangerous patterns."""
        # Remove injection patterns
        for pattern in self.injection_patterns:
            query = pattern.sub('', query)
        
        # Remove null bytes
        query = query.replace('\x00', '')
        
        # Remove control characters
        query = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', query)
        
        # Strip whitespace
        query = query.strip()
        
        return query
    
    def detect_injection_attempts(self, query: str) -> List[str]:
        """Detect all injection attempts in a query."""
        attempts = []
        
        for pattern in self.injection_patterns:
            if pattern.search(query):
                attempts.append(pattern.pattern)
        
        return attempts


class RateLimiter:
    """
    Rate limiting for API requests.
    
    Implements sliding window rate limiting.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        
        # Track requests per user
        self._requests: Dict[str, List[float]] = {}
        
        logger.info(f"RateLimiter initialized (max_requests={max_requests}, window={window_seconds}s)")
    
    def check_rate_limit(self, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a user has exceeded rate limit.
        
        Returns:
            Tuple of (is_allowed, metadata)
        """
        current_time = time.time()
        
        # Initialize user if not exists
        if user_id not in self._requests:
            self._requests[user_id] = []
        
        # Remove old requests outside window
        cutoff = current_time - self.window_seconds
        self._requests[user_id] = [
            t for t in self._requests[user_id]
            if t > cutoff
        ]
        
        # Check if limit exceeded
        request_count = len(self._requests[user_id])
        
        if request_count >= self.max_requests:
            # Calculate when the oldest request will expire
            oldest_request = min(self._requests[user_id])
            reset_time = oldest_request + self.window_seconds
            retry_after = reset_time - current_time
            
            metadata = {
                "allowed": False,
                "limit": self.max_requests,
                "remaining": 0,
                "reset_time": reset_time,
                "retry_after_seconds": retry_after,
            }
            
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False, metadata
        
        # Record request
        self._requests[user_id].append(current_time)
        
        metadata = {
            "allowed": True,
            "limit": self.max_requests,
            "remaining": self.max_requests - request_count - 1,
            "reset_time": current_time + self.window_seconds,
        }
        
        return True, metadata
    
    def get_remaining(self, user_id: str) -> int:
        """Get remaining requests for a user."""
        current_time = time.time()
        
        if user_id not in self._requests:
            return self.max_requests
        
        # Clean old requests
        cutoff = current_time - self.window_seconds
        self._requests[user_id] = [
            t for t in self._requests[user_id]
            if t > cutoff
        ]
        
        return max(0, self.max_requests - len(self._requests[user_id]))
    
    def reset(self, user_id: Optional[str] = None) -> None:
        """Reset rate limit for a user or all users."""
        if user_id:
            if user_id in self._requests:
                del self._requests[user_id]
                logger.info(f"Rate limit reset for user {user_id}")
        else:
            self._requests.clear()
            logger.info("Rate limit reset for all users")


class SecurityAuditLogger:
    """
    Log security events for audit and analysis.
    """
    
    def __init__(self, log_dir: str = "logs/security"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SecurityAuditLogger initialized, logging to {log_dir}")
    
    def log_event(
        self,
        event_type: str,
        severity: str,
        user_id: Optional[str],
        details: Dict[str, Any],
    ) -> None:
        """Log a security event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "details": details,
        }
        
        # Log to file
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d")
            log_file = self.log_dir / f"security_{timestamp}.jsonl"
            
            with open(log_file, "a") as f:
                import json
                f.write(json.dumps(event) + "\n")
            
            # Also log to logger
            log_func = getattr(logger, severity.lower(), logger.info)
            log_func(f"Security event: {event_type} - {details}")
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def log_injection_attempt(
        self,
        user_id: Optional[str],
        query: str,
        patterns_detected: List[str],
    ) -> None:
        """Log a prompt injection attempt."""
        self.log_event(
            event_type="prompt_injection_attempt",
            severity="warning",
            user_id=user_id,
            details={
                "query_preview": query[:100],
                "patterns_detected": patterns_detected,
                "query_length": len(query),
            },
        )
    
    def log_document_validation_failure(
        self,
        user_id: Optional[str],
        file_path: str,
        reason: str,
    ) -> None:
        """Log a document validation failure."""
        self.log_event(
            event_type="document_validation_failure",
            severity="warning",
            user_id=user_id,
            details={
                "file_path": file_path,
                "reason": reason,
            },
        )
    
    def log_rate_limit_exceeded(
        self,
        user_id: str,
        limit: int,
        retry_after: float,
    ) -> None:
        """Log a rate limit violation."""
        self.log_event(
            event_type="rate_limit_exceeded",
            severity="warning",
            user_id=user_id,
            details={
                "limit": limit,
                "retry_after_seconds": retry_after,
            },
        )


# Global security instances
document_validator = DocumentValidator()
query_validator = QueryValidator()
rate_limiter = RateLimiter()
security_audit_logger = SecurityAuditLogger()


def get_document_validator() -> DocumentValidator:
    """Get the global document validator."""
    return document_validator


def get_query_validator() -> QueryValidator:
    """Get the global query validator."""
    return query_validator


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter."""
    return rate_limiter


def get_security_audit_logger() -> SecurityAuditLogger:
    """Get the global security audit logger."""
    return security_audit_logger

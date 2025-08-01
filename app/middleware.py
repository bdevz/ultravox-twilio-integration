"""
Middleware for request processing and correlation ID tracking.
"""

import time
import logging
import json
import re
import html
from typing import Callable, Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError

from app.logging_config import generate_correlation_id, set_correlation_id, get_correlation_id


logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation ID for request tracking."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with correlation ID tracking.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or generate_correlation_id()
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Add correlation ID to request state for access in handlers
        request.state.correlation_id = correlation_id
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Record metrics
            process_time = time.time() - start_time
            try:
                from app.metrics import get_metrics_collector, record_metric
                
                # Record request metrics
                get_metrics_collector().record_request(
                    request.method, 
                    request.url.path, 
                    response.status_code
                )
                
                # Record response time metric
                record_metric(
                    "request_duration_ms",
                    process_time * 1000,
                    tags={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": str(response.status_code)
                    },
                    correlation_id=correlation_id
                )
                
            except ImportError:
                # Handle case where metrics module isn't available
                pass
            
            # Log request completion
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4),
                    "correlation_id": correlation_id
                }
            )
            
            return response
            
        except Exception as e:
            # Record error metrics
            process_time = time.time() - start_time
            try:
                from app.metrics import get_metrics_collector, record_metric
                
                # Record failed request metrics (use 500 as default error status)
                get_metrics_collector().record_request(
                    request.method, 
                    request.url.path, 
                    500
                )
                
                # Record error response time metric
                record_metric(
                    "request_duration_ms",
                    process_time * 1000,
                    tags={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": "500",
                        "error": "true"
                    },
                    correlation_id=correlation_id
                )
                
                # Record error count metric
                record_metric(
                    "request_errors_total",
                    1,
                    tags={
                        "method": request.method,
                        "path": request.url.path,
                        "error_type": type(e).__name__
                    },
                    correlation_id=correlation_id
                )
                
            except ImportError:
                # Handle case where metrics module isn't available
                pass
            
            # Log request error
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": round(process_time, 4),
                    "correlation_id": correlation_id,
                    "exception": str(e)
                },
                exc_info=True
            )
            raise


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for detailed request/response logging."""
    
    def __init__(self, app, log_request_body: bool = False, log_response_body: bool = False):
        """
        Initialize request logging middleware.
        
        Args:
            app: FastAPI application
            log_request_body: Whether to log request body
            log_response_body: Whether to log response body
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with detailed logging.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
        """
        correlation_id = get_correlation_id()
        
        # Log request details
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None,
            "correlation_id": correlation_id
        }
        
        # Log request body if enabled and present
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Decode body for logging (be careful with sensitive data)
                    request_data["body_size"] = len(body)
                    # Only log first 1000 characters to avoid huge logs
                    body_str = body.decode("utf-8")[:1000]
                    if len(body_str) == 1000:
                        body_str += "... (truncated)"
                    request_data["body_preview"] = body_str
            except Exception as e:
                request_data["body_error"] = str(e)
        
        logger.debug("Incoming request", extra=request_data)
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response details
        response_data = {
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "response_headers": dict(response.headers),
            "correlation_id": correlation_id
        }
        
        # Log response body if enabled (be very careful with this in production)
        if self.log_response_body and hasattr(response, 'body'):
            try:
                # This is complex and may not work for all response types
                response_data["response_body_available"] = True
            except Exception as e:
                response_data["response_body_error"] = str(e)
        
        logger.debug("Outgoing response", extra=response_data)
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request validation."""
    
    def __init__(self, app, max_content_length: int = 1024 * 1024):  # 1MB default
        """
        Initialize request validation middleware.
        
        Args:
            app: FastAPI application
            max_content_length: Maximum allowed content length in bytes
        """
        super().__init__(app)
        self.max_content_length = max_content_length
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate incoming requests.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
            
        Raises:
            HTTPException: For validation errors
        """
        correlation_id = get_correlation_id()
        
        try:
            # Validate content length
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_content_length:
                logger.warning(
                    f"Request content too large: {content_length} bytes",
                    extra={"correlation_id": correlation_id, "max_allowed": self.max_content_length}
                )
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "payload_too_large",
                        "message": f"Request content exceeds maximum allowed size of {self.max_content_length} bytes",
                        "max_size": self.max_content_length
                    }
                )
            
            # Validate content type for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "")
                if not content_type.startswith("application/json"):
                    logger.warning(
                        f"Invalid content type: {content_type}",
                        extra={"correlation_id": correlation_id, "method": request.method}
                    )
                    raise HTTPException(
                        status_code=415,
                        detail={
                            "error": "unsupported_media_type",
                            "message": "Content-Type must be application/json for POST/PUT/PATCH requests",
                            "received_content_type": content_type
                        }
                    )
            
            # Validate JSON payload structure for specific endpoints
            if request.method in ["POST", "PUT", "PATCH"] and request.url.path.startswith("/api/v1/"):
                await self._validate_json_payload(request)
            
            # Continue with request processing
            response = await call_next(request)
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(
                f"Request validation error: {str(e)}",
                extra={"correlation_id": correlation_id, "path": request.url.path},
                exc_info=True
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "request_validation_failed",
                    "message": "Request validation encountered an unexpected error"
                }
            )
    
    async def _validate_json_payload(self, request: Request) -> None:
        """
        Validate JSON payload structure.
        
        Args:
            request: FastAPI request object
            
        Raises:
            HTTPException: For invalid JSON
        """
        try:
            # Read and parse JSON body
            body = await request.body()
            if body:
                try:
                    json_data = json.loads(body.decode("utf-8"))
                    
                    # Validate JSON structure based on endpoint
                    if "/calls/" in request.url.path and request.method == "POST":
                        self._validate_call_request_structure(json_data)
                    elif "/agents" in request.url.path and request.method in ["POST", "PUT"]:
                        self._validate_agent_request_structure(json_data)
                        
                except json.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "invalid_json",
                            "message": "Request body contains invalid JSON",
                            "details": str(e)
                        }
                    )
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"JSON validation error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "json_validation_failed",
                    "message": "Failed to validate JSON payload"
                }
            )
    
    def _validate_call_request_structure(self, data: Dict[str, Any]) -> None:
        """
        Validate call request JSON structure.
        
        Args:
            data: Parsed JSON data
            
        Raises:
            HTTPException: For invalid structure
        """
        required_fields = ["phone_number", "agent_id"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "missing_required_fields",
                    "message": f"Missing required fields: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields,
                    "required_fields": required_fields
                }
            )
        
        # Validate template_context if present
        if "template_context" in data and data["template_context"] is not None:
            if not isinstance(data["template_context"], dict):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_template_context",
                        "message": "template_context must be a JSON object",
                        "received_type": type(data["template_context"]).__name__
                    }
                )
    
    def _validate_agent_request_structure(self, data: Dict[str, Any]) -> None:
        """
        Validate agent request JSON structure.
        
        Args:
            data: Parsed JSON data
            
        Raises:
            HTTPException: For invalid structure
        """
        required_fields = ["name", "prompt"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "missing_required_fields",
                    "message": f"Missing required fields: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields,
                    "required_fields": required_fields
                }
            )
        
        # Validate template_variables if present
        if "template_variables" in data and data["template_variables"] is not None:
            if not isinstance(data["template_variables"], dict):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_template_variables",
                        "message": "template_variables must be a JSON object",
                        "received_type": type(data["template_variables"]).__name__
                    }
                )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add comprehensive security headers to responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response with security headers
        """
        response = await call_next(request)
        
        # Add comprehensive security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Enhanced Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # Allow inline scripts for API docs
            "style-src 'self' 'unsafe-inline'",   # Allow inline styles for API docs
            "img-src 'self' data:",               # Allow data URIs for images
            "connect-src 'self'",                 # Restrict AJAX/WebSocket connections
            "font-src 'self'",                    # Restrict font sources
            "object-src 'none'",                  # Disable plugins
            "media-src 'self'",                   # Restrict media sources
            "frame-src 'none'",                   # Disable frames
            "base-uri 'self'",                    # Restrict base URI
            "form-action 'self'"                  # Restrict form submissions
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Strict Transport Security (HSTS) - only add if HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Permissions Policy (formerly Feature Policy)
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "speaker=()",
            "vibrate=()",
            "fullscreen=(self)",
            "sync-xhr=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)
        
        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]
        
        # Remove potentially sensitive headers
        headers_to_remove = ["x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"]
        for header in headers_to_remove:
            if header in response.headers:
                del response.headers[header]
        
        return response


class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for API key validation and secure header handling."""
    
    def __init__(self, app, required_for_paths: Optional[list] = None):
        """
        Initialize API key validation middleware.
        
        Args:
            app: FastAPI application
            required_for_paths: List of path patterns that require API key validation
        """
        super().__init__(app)
        self.required_for_paths = required_for_paths or ["/api/v1/"]
        self.api_key_header = "X-API-Key"
        self.valid_api_keys = self._load_valid_api_keys()
    
    def _load_valid_api_keys(self) -> set:
        """
        Load valid API keys from environment variables.
        
        Returns:
            set: Set of valid API keys
        """
        import os
        
        # Load API keys from environment (comma-separated)
        api_keys_env = os.getenv("VALID_API_KEYS", "")
        if api_keys_env:
            return set(key.strip() for key in api_keys_env.split(",") if key.strip())
        
        # For development, allow a default key if specified
        dev_key = os.getenv("DEV_API_KEY")
        if dev_key:
            return {dev_key}
        
        return set()
    
    def _get_current_api_keys(self) -> set:
        """
        Get current API keys (reload from environment for testing).
        
        Returns:
            set: Set of current valid API keys
        """
        # For testing purposes, always reload from environment
        # In production, this could be cached for performance
        return self._load_valid_api_keys()
    
    def _requires_api_key(self, path: str) -> bool:
        """
        Check if the given path requires API key validation.
        
        Args:
            path: Request path
            
        Returns:
            bool: True if API key is required
        """
        # Skip API key validation for health checks and docs
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
        if any(path.startswith(skip_path) for skip_path in skip_paths):
            return False
        
        # Check if path matches required patterns
        return any(path.startswith(pattern) for pattern in self.required_for_paths)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate API key for protected endpoints.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
            
        Raises:
            HTTPException: For authentication errors
        """
        correlation_id = get_correlation_id()
        
        # Check if API key validation is required for this path
        if not self._requires_api_key(request.url.path):
            return await call_next(request)
        
        # Get current API keys (reload for testing)
        current_api_keys = self._get_current_api_keys()
        
        # Skip validation if no API keys are configured (development mode)
        if not current_api_keys:
            logger.warning(
                "API key validation skipped - no valid keys configured",
                extra={"correlation_id": correlation_id, "path": request.url.path}
            )
            return await call_next(request)
        
        # Extract API key from headers
        api_key = request.headers.get(self.api_key_header)
        
        if not api_key:
            logger.warning(
                "API key missing from request",
                extra={"correlation_id": correlation_id, "path": request.url.path}
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "api_key_required",
                    "message": f"API key required in {self.api_key_header} header",
                    "required_header": self.api_key_header
                }
            )
        
        # Validate API key
        if api_key not in current_api_keys:
            logger.warning(
                "Invalid API key provided",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "***"
                }
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_api_key",
                    "message": "Invalid API key provided"
                }
            )
        
        # Log successful authentication
        logger.debug(
            "API key validation successful",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "***"
            }
        )
        
        return await call_next(request)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API endpoints."""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per IP
            requests_per_hour: Maximum requests per hour per IP
            burst_limit: Maximum burst requests allowed
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        
        # Storage for rate limiting data
        self.minute_buckets = defaultdict(lambda: deque())
        self.hour_buckets = defaultdict(lambda: deque())
        self.burst_buckets = defaultdict(lambda: deque())
        
        # Cleanup interval tracking
        self.last_cleanup = datetime.now()
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Client IP address
        """
        # Check for forwarded headers (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_entries(self):
        """Clean up old entries from rate limiting buckets."""
        now = datetime.now()
        
        # Only cleanup every 5 minutes to avoid performance impact
        if (now - self.last_cleanup).total_seconds() < 300:
            return
        
        self.last_cleanup = now
        
        # Clean up minute buckets (keep last 2 minutes)
        minute_cutoff = now - timedelta(minutes=2)
        for ip in list(self.minute_buckets.keys()):
            bucket = self.minute_buckets[ip]
            while bucket and bucket[0] < minute_cutoff:
                bucket.popleft()
            if not bucket:
                del self.minute_buckets[ip]
        
        # Clean up hour buckets (keep last 2 hours)
        hour_cutoff = now - timedelta(hours=2)
        for ip in list(self.hour_buckets.keys()):
            bucket = self.hour_buckets[ip]
            while bucket and bucket[0] < hour_cutoff:
                bucket.popleft()
            if not bucket:
                del self.hour_buckets[ip]
        
        # Clean up burst buckets (keep last 10 seconds)
        burst_cutoff = now - timedelta(seconds=10)
        for ip in list(self.burst_buckets.keys()):
            bucket = self.burst_buckets[ip]
            while bucket and bucket[0] < burst_cutoff:
                bucket.popleft()
            if not bucket:
                del self.burst_buckets[ip]
    
    def _is_rate_limited(self, client_ip: str) -> tuple[bool, str, int]:
        """
        Check if client is rate limited.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            tuple: (is_limited, limit_type, retry_after_seconds)
        """
        now = datetime.now()
        
        # Check burst limit (10 requests in 10 seconds)
        burst_cutoff = now - timedelta(seconds=10)
        burst_bucket = self.burst_buckets[client_ip]
        
        # Remove old entries
        while burst_bucket and burst_bucket[0] < burst_cutoff:
            burst_bucket.popleft()
        
        if len(burst_bucket) >= self.burst_limit:
            return True, "burst", 10
        
        # Check minute limit
        minute_cutoff = now - timedelta(minutes=1)
        minute_bucket = self.minute_buckets[client_ip]
        
        # Remove old entries
        while minute_bucket and minute_bucket[0] < minute_cutoff:
            minute_bucket.popleft()
        
        if len(minute_bucket) >= self.requests_per_minute:
            return True, "minute", 60
        
        # Check hour limit
        hour_cutoff = now - timedelta(hours=1)
        hour_bucket = self.hour_buckets[client_ip]
        
        # Remove old entries
        while hour_bucket and hour_bucket[0] < hour_cutoff:
            hour_bucket.popleft()
        
        if len(hour_bucket) >= self.requests_per_hour:
            return True, "hour", 3600
        
        return False, "", 0
    
    def _record_request(self, client_ip: str):
        """
        Record a request for rate limiting.
        
        Args:
            client_ip: Client IP address
        """
        now = datetime.now()
        
        # Record in all buckets
        self.burst_buckets[client_ip].append(now)
        self.minute_buckets[client_ip].append(now)
        self.hour_buckets[client_ip].append(now)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Apply rate limiting to requests.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
            
        Raises:
            HTTPException: For rate limit exceeded
        """
        correlation_id = get_correlation_id()
        
        # Skip rate limiting for health checks and docs
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Clean up old entries periodically
        self._cleanup_old_entries()
        
        # Check rate limits
        is_limited, limit_type, retry_after = self._is_rate_limited(client_ip)
        
        if is_limited:
            logger.warning(
                f"Rate limit exceeded for {client_ip}",
                extra={
                    "correlation_id": correlation_id,
                    "client_ip": client_ip,
                    "limit_type": limit_type,
                    "retry_after": retry_after,
                    "path": request.url.path
                }
            )
            
            # Create rate limit response
            response = Response(
                content=json.dumps({
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded: too many requests per {limit_type}",
                    "limit_type": limit_type,
                    "retry_after": retry_after
                }),
                status_code=429,
                media_type="application/json"
            )
            
            # Add rate limit headers
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(
                self.burst_limit if limit_type == "burst" 
                else self.requests_per_minute if limit_type == "minute"
                else self.requests_per_hour
            )
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int((datetime.now() + timedelta(seconds=retry_after)).timestamp()))
            
            return response
        
        # Record the request
        self._record_request(client_ip)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        minute_bucket = self.minute_buckets[client_ip]
        remaining_minute = max(0, self.requests_per_minute - len(minute_bucket))
        
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining_minute)
        response.headers["X-RateLimit-Reset"] = str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
        
        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware for input sanitization, especially for template context variables."""
    
    def __init__(self, app):
        """
        Initialize input sanitization middleware.
        
        Args:
            app: FastAPI application
        """
        super().__init__(app)
        
        # Patterns for potentially dangerous content
        self.dangerous_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'vbscript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers like onclick=
            re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL),
            re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL),
            re.compile(r'<embed[^>]*>', re.IGNORECASE),
            re.compile(r'<link[^>]*>', re.IGNORECASE),
            re.compile(r'<meta[^>]*>', re.IGNORECASE),
        ]
        
        # SQL injection patterns
        self.sql_patterns = [
            re.compile(r'\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b', re.IGNORECASE),
            re.compile(r'[\'";].*(-{2}|/\*|\*/)', re.IGNORECASE),
            re.compile(r'\b(or|and)\s+[\'"]?\d+[\'"]?\s*=\s*[\'"]?\d+[\'"]?', re.IGNORECASE),
        ]
    
    def _sanitize_string(self, value: str) -> str:
        """
        Sanitize a string value.
        
        Args:
            value: String to sanitize
            
        Returns:
            str: Sanitized string
        """
        if not isinstance(value, str):
            return value
        
        # HTML encode to prevent XSS
        sanitized = html.escape(value)
        
        # Remove dangerous patterns
        for pattern in self.dangerous_patterns:
            sanitized = pattern.sub('', sanitized)
        
        # Check for SQL injection patterns and log warnings
        for pattern in self.sql_patterns:
            if pattern.search(value):
                logger.warning(
                    "Potential SQL injection attempt detected",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "suspicious_content": value[:100] + "..." if len(value) > 100 else value
                    }
                )
                # For SQL patterns, we'll be more aggressive and remove the content
                sanitized = pattern.sub('[FILTERED]', sanitized)
        
        return sanitized
    
    def _sanitize_dict(self, data: dict) -> dict:
        """
        Recursively sanitize dictionary values.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            dict: Sanitized dictionary
        """
        sanitized = {}
        for key, value in data.items():
            # Sanitize key as well
            clean_key = self._sanitize_string(str(key)) if isinstance(key, str) else key
            
            if isinstance(value, str):
                sanitized[clean_key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[clean_key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[clean_key] = self._sanitize_list(value)
            else:
                sanitized[clean_key] = value
        
        return sanitized
    
    def _sanitize_list(self, data: list) -> list:
        """
        Recursively sanitize list values.
        
        Args:
            data: List to sanitize
            
        Returns:
            list: Sanitized list
        """
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(self._sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(self._sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self._sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Sanitize request input, especially template context variables.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
        """
        correlation_id = get_correlation_id()
        
        # Only sanitize POST/PUT/PATCH requests with JSON content
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                try:
                    # Read and parse the request body
                    body = await request.body()
                    if body:
                        try:
                            json_data = json.loads(body.decode("utf-8"))
                            
                            # Sanitize the JSON data
                            sanitized_data = self._sanitize_dict(json_data) if isinstance(json_data, dict) else json_data
                            
                            # Check if sanitization made changes
                            if sanitized_data != json_data:
                                logger.info(
                                    "Input sanitization applied to request",
                                    extra={
                                        "correlation_id": correlation_id,
                                        "path": request.url.path,
                                        "changes_made": True
                                    }
                                )
                            
                            # Replace the request body with sanitized data
                            sanitized_body = json.dumps(sanitized_data).encode("utf-8")
                            
                            # Create a new request with sanitized body
                            async def receive():
                                return {
                                    "type": "http.request",
                                    "body": sanitized_body,
                                    "more_body": False
                                }
                            
                            # Update the request's receive callable
                            request._receive = receive
                            
                        except json.JSONDecodeError:
                            # If JSON is invalid, let it pass through - validation middleware will handle it
                            pass
                            
                except Exception as e:
                    logger.error(
                        f"Error during input sanitization: {str(e)}",
                        extra={"correlation_id": correlation_id},
                        exc_info=True
                    )
                    # Continue processing even if sanitization fails
        
        return await call_next(request)
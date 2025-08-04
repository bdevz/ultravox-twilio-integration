"""
HTTP client service for external API calls with retry logic and error handling.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError, ClientResponseError
from pydantic import BaseModel

from app.exceptions import (
    NetworkError,
    TimeoutError,
    UltravoxAPIError,
    TwilioAPIError,
    AuthenticationError,
    RateLimitError
)
from app.logging_config import LoggerMixin, get_correlation_id


logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class HTTPClientTimeoutError(HTTPClientError):
    """Exception for HTTP timeout errors."""
    pass


class HTTPClientConnectionError(HTTPClientError):
    """Exception for HTTP connection errors."""
    pass


class HTTPClientResponseError(HTTPClientError):
    """Exception for HTTP response errors."""
    pass


class RetryConfig(BaseModel):
    """Configuration for retry logic."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class HTTPClientService(LoggerMixin):
    """Service for making HTTP requests with retry logic and error handling."""
    
    def __init__(self, timeout: float = 30.0, retry_config: Optional[RetryConfig] = None):
        """
        Initialize HTTP client service.
        
        Args:
            timeout: Request timeout in seconds
            retry_config: Retry configuration
        """
        self.timeout = ClientTimeout(total=timeout)
        self.retry_config = retry_config or RetryConfig()
        self._session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Ultravox-Twilio-Integration/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None
    ) -> Any:
        """
        Make an HTTP request with retry logic and metrics collection.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Request URL
            headers: Additional headers
            data: Request body data
            params: Query parameters
            auth_token: Authorization token
            
        Returns:
            dict: Parsed JSON response
            
        Raises:
            HTTPClientError: For various HTTP client errors
        """
        await self._ensure_session()
        
        # Import metrics here to avoid circular imports
        try:
            from app.metrics import get_metrics_collector
            metrics_available = True
        except ImportError:
            metrics_available = False
        
        correlation_id = get_correlation_id()
        start_time = time.time()
        
        # Prepare headers
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        if auth_token:
            request_headers['Authorization'] = f'Bearer {auth_token}'
        
        # Prepare request data
        request_data = None
        if data:
            if isinstance(data, dict):
                request_data = json.dumps(data)
                request_headers['Content-Type'] = 'application/json'
            else:
                request_data = data
        
        # Log request details
        self.logger.info(
            f"Making HTTP request: {method} {url}",
            extra={
                "http_method": method,
                "http_url": url,
                "http_has_auth": bool(auth_token),
                "http_has_data": bool(data),
                "http_params": params or {},
                "correlation_id": correlation_id
            }
        )
        
        # Execute request with retry logic
        last_exception = None
        status_code = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                async with self._session.request(
                    method=method.upper(),
                    url=url,
                    headers=request_headers,
                    data=request_data,
                    params=params
                ) as response:
                    status_code = response.status
                    result = await self._handle_response(response)
                    
                    # Record successful request metrics
                    duration_ms = (time.time() - start_time) * 1000
                    if metrics_available:
                        get_metrics_collector().record_api_call(
                            endpoint=url,
                            method=method,
                            service="external",
                            duration_ms=duration_ms,
                            status_code=status_code,
                            success=True,
                            correlation_id=correlation_id
                        )
                    
                    self.logger.info(
                        f"HTTP request completed successfully: {method} {url}",
                        extra={
                            "http_method": method,
                            "http_url": url,
                            "http_status_code": status_code,
                            "http_duration_ms": round(duration_ms, 2),
                            "http_attempt": attempt + 1,
                            "correlation_id": correlation_id
                        }
                    )
                    
                    return result
                    
            except (asyncio.TimeoutError, aiohttp.ServerTimeoutError) as e:
                duration_ms = (time.time() - start_time) * 1000
                last_exception = TimeoutError(
                    operation=f"{method} {url}",
                    timeout_seconds=self.timeout.total,
                    details={'url': url, 'method': method, 'attempt': attempt + 1}
                )
                self.logger.warning(
                    f"Request timeout on attempt {attempt + 1}: {url}",
                    extra={
                        "http_method": method,
                        "http_url": url,
                        "http_duration_ms": round(duration_ms, 2),
                        "http_attempt": attempt + 1,
                        "http_error": "timeout",
                        "correlation_id": correlation_id
                    }
                )
                
            except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError) as e:
                duration_ms = (time.time() - start_time) * 1000
                last_exception = NetworkError(
                    f"Connection error: {str(e)}",
                    details={'url': url, 'method': method, 'attempt': attempt + 1}
                )
                self.logger.warning(
                    f"Connection error on attempt {attempt + 1}: {url} - {str(e)}",
                    extra={
                        "http_method": method,
                        "http_url": url,
                        "http_duration_ms": round(duration_ms, 2),
                        "http_attempt": attempt + 1,
                        "http_error": "connection_error",
                        "http_error_details": str(e),
                        "correlation_id": correlation_id
                    }
                )
                
            except HTTPClientResponseError as e:
                duration_ms = (time.time() - start_time) * 1000
                status_code = e.status_code
                
                # Convert to appropriate exception based on status code
                if e.status_code == 401:
                    # Record failed request metrics
                    if metrics_available:
                        get_metrics_collector().record_api_call(
                            endpoint=url,
                            method=method,
                            service="external",
                            duration_ms=duration_ms,
                            status_code=status_code,
                            success=False,
                            error_type="AuthenticationError",
                            correlation_id=correlation_id
                        )
                    
                    raise AuthenticationError(
                        "Authentication failed",
                        details={'url': url, 'method': method, 'status_code': e.status_code}
                    )
                elif e.status_code == 429:
                    # Record failed request metrics
                    if metrics_available:
                        get_metrics_collector().record_api_call(
                            endpoint=url,
                            method=method,
                            service="external",
                            duration_ms=duration_ms,
                            status_code=status_code,
                            success=False,
                            error_type="RateLimitError",
                            correlation_id=correlation_id
                        )
                    
                    raise RateLimitError(
                        "Rate limit exceeded",
                        details={'url': url, 'method': method, 'status_code': e.status_code}
                    )
                elif e.status_code and 400 <= e.status_code < 500:
                    # Don't retry client errors (4xx)
                    if metrics_available:
                        get_metrics_collector().record_api_call(
                            endpoint=url,
                            method=method,
                            service="external",
                            duration_ms=duration_ms,
                            status_code=status_code,
                            success=False,
                            error_type="ClientError",
                            correlation_id=correlation_id
                        )
                    
                    self.logger.error(
                        f"Client error {e.status_code}: {e.message}",
                        extra={
                            "http_method": method,
                            "http_url": url,
                            "http_status_code": e.status_code,
                            "http_duration_ms": round(duration_ms, 2),
                            "http_error": "client_error",
                            "correlation_id": correlation_id
                        }
                    )
                    raise e
                
                last_exception = e
                self.logger.warning(
                    f"Server error on attempt {attempt + 1}: {e.message}",
                    extra={
                        "http_method": method,
                        "http_url": url,
                        "http_status_code": e.status_code,
                        "http_duration_ms": round(duration_ms, 2),
                        "http_attempt": attempt + 1,
                        "http_error": "server_error",
                        "correlation_id": correlation_id
                    }
                )
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                last_exception = HTTPClientError(
                    f"Unexpected error: {str(e)}",
                    details={'url': url, 'method': method, 'attempt': attempt + 1}
                )
                self.logger.error(
                    f"Unexpected error on attempt {attempt + 1}: {url} - {str(e)}",
                    extra={
                        "http_method": method,
                        "http_url": url,
                        "http_duration_ms": round(duration_ms, 2),
                        "http_attempt": attempt + 1,
                        "http_error": "unexpected_error",
                        "http_error_details": str(e),
                        "correlation_id": correlation_id
                    }
                )
            
            # Don't wait after the last attempt
            if attempt < self.retry_config.max_retries:
                delay = self._calculate_retry_delay(attempt)
                self.logger.debug(f"Waiting {delay:.2f}s before retry")
                await asyncio.sleep(delay)
        
        # All retries exhausted - record final failure metrics
        final_duration_ms = (time.time() - start_time) * 1000
        if metrics_available:
            get_metrics_collector().record_api_call(
                endpoint=url,
                method=method,
                service="external",
                duration_ms=final_duration_ms,
                status_code=status_code,
                success=False,
                error_type=type(last_exception).__name__ if last_exception else "UnknownError",
                correlation_id=correlation_id
            )
        
        self.logger.error(
            f"All {self.retry_config.max_retries + 1} attempts failed for {method} {url}",
            extra={
                "http_method": method,
                "http_url": url,
                "http_total_duration_ms": round(final_duration_ms, 2),
                "http_total_attempts": self.retry_config.max_retries + 1,
                "correlation_id": correlation_id
            }
        )
        
        if last_exception:
            raise last_exception
        else:
            raise NetworkError(f"Request failed after {self.retry_config.max_retries + 1} attempts")
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """
        Handle HTTP response and parse JSON.
        
        Args:
            response: aiohttp ClientResponse
            
        Returns:
            Any: Parsed JSON response (dict, list, or other JSON types)
            
        Raises:
            HTTPClientResponseError: For HTTP error responses
        """
        try:
            # Read response text
            response_text = await response.text()
            
            # Check for HTTP errors
            if not response.ok:
                error_details = {
                    'status_code': response.status,
                    'url': str(response.url),
                    'headers': dict(response.headers),
                    'response_text': response_text[:1000]  # Limit response text length
                }
                
                # Try to parse error response as JSON
                try:
                    error_data = json.loads(response_text) if response_text else {}
                    error_details['error_data'] = error_data
                    
                    # Handle different error response formats
                    if isinstance(error_data, dict):
                        error_message = error_data.get('message', f'HTTP {response.status} error')
                    elif isinstance(error_data, list) and error_data:
                        # If it's a list, try to get the first item or convert to string
                        first_item = error_data[0]
                        if isinstance(first_item, dict):
                            error_message = first_item.get('message', str(first_item))
                        else:
                            error_message = str(first_item)
                    else:
                        error_message = f'HTTP {response.status} error'
                except json.JSONDecodeError:
                    error_message = f'HTTP {response.status} error'
                
                raise HTTPClientResponseError(
                    error_message,
                    status_code=response.status,
                    details=error_details
                )
            
            # Parse JSON response
            if not response_text:
                return {}
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                raise HTTPClientError(
                    f"Failed to parse JSON response: {str(e)}",
                    status_code=response.status,
                    details={'response_text': response_text[:500]}
                )
                
        except HTTPClientResponseError:
            raise
        except Exception as e:
            raise HTTPClientError(
                f"Error handling response: {str(e)}",
                status_code=getattr(response, 'status', None)
            )
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            float: Delay in seconds
        """
        delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt)
        delay = min(delay, self.retry_config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    async def make_ultravox_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.ultravox.ai"
    ) -> Dict[str, Any]:
        """
        Make a request to Ultravox API with metrics collection.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            data: Request data
            api_key: Ultravox API key
            base_url: Ultravox base URL
            
        Returns:
            dict: API response
            
        Raises:
            HTTPClientError: For API errors
        """
        try:
            from app.metrics import track_api_call
        except ImportError:
            from contextlib import asynccontextmanager
            
            @asynccontextmanager
            async def track_api_call(*args, **kwargs):
                yield {}
        
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        correlation_id = get_correlation_id()
        
        async with track_api_call(endpoint, method, "ultravox", correlation_id) as context:
            try:
                self.logger.info(
                    f"Making Ultravox API request: {method} {endpoint}",
                    extra={
                        "ultravox_endpoint": endpoint,
                        "ultravox_method": method,
                        "ultravox_has_data": bool(data),
                        "correlation_id": correlation_id
                    }
                )
                
                # Ultravox uses X-API-Key header, not Bearer token
                headers = {'X-API-Key': api_key} if api_key else {}
                
                result = await self.make_request(
                    method=method,
                    url=url,
                    data=data,
                    headers=headers
                )
                
                self.logger.info(
                    f"Ultravox API request successful: {method} {endpoint}",
                    extra={
                        "ultravox_endpoint": endpoint,
                        "ultravox_method": method,
                        "correlation_id": correlation_id
                    }
                )
                
                return result
                
            except (AuthenticationError, RateLimitError, TimeoutError, NetworkError):
                # Re-raise specific exceptions as-is
                raise
            except HTTPClientError as e:
                context["status_code"] = e.status_code
                self.logger.error(
                    f"Ultravox API error: {e.message}",
                    extra={
                        "ultravox_endpoint": endpoint,
                        "ultravox_method": method,
                        "ultravox_status_code": e.status_code,
                        "ultravox_error": e.message,
                        "correlation_id": correlation_id
                    }
                )
                
                # Convert to Ultravox-specific error
                details = e.details or {}
                details.update({
                    'service': 'ultravox',
                    'endpoint': endpoint,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                raise UltravoxAPIError(
                    f"Ultravox API error: {e.message}",
                    details=details,
                    status_code=e.status_code or 502
                )
    
    async def make_twilio_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        base_url: str = "https://api.twilio.com"
    ) -> Dict[str, Any]:
        """
        Make a request to Twilio API with metrics collection.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            data: Request data
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            base_url: Twilio base URL
            
        Returns:
            dict: API response
            
        Raises:
            HTTPClientError: For API errors
        """
        try:
            from app.metrics import track_api_call
        except ImportError:
            from contextlib import asynccontextmanager
            
            @asynccontextmanager
            async def track_api_call(*args, **kwargs):
                yield {}
        
        await self._ensure_session()
        
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        correlation_id = get_correlation_id()
        
        async with track_api_call(endpoint, method, "twilio", correlation_id) as context:
            # Twilio uses Basic Auth and form data
            headers = {}
            if account_sid and auth_token:
                import base64
                credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
                headers['Authorization'] = f'Basic {credentials}'
            
            # Twilio expects form data, not JSON
            form_data = None
            if data:
                form_data = aiohttp.FormData()
                for key, value in data.items():
                    form_data.add_field(key, str(value))
            
            try:
                self.logger.info(
                    f"Making Twilio API request: {method} {endpoint}",
                    extra={
                        "twilio_endpoint": endpoint,
                        "twilio_method": method,
                        "twilio_has_data": bool(data),
                        "correlation_id": correlation_id
                    }
                )
                
                start_time = time.time()
                
                async with self._session.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    data=form_data
                ) as response:
                    context["status_code"] = response.status
                    result = await self._handle_response(response)
                    
                    duration_ms = (time.time() - start_time) * 1000
                    self.logger.info(
                        f"Twilio API request successful: {method} {endpoint}",
                        extra={
                            "twilio_endpoint": endpoint,
                            "twilio_method": method,
                            "twilio_status_code": response.status,
                            "twilio_duration_ms": round(duration_ms, 2),
                            "correlation_id": correlation_id
                        }
                    )
                    
                    return result
                    
            except (AuthenticationError, RateLimitError, TimeoutError, NetworkError):
                # Re-raise specific exceptions as-is
                raise
            except HTTPClientError as e:
                context["status_code"] = e.status_code
                self.logger.error(
                    f"Twilio API error: {e.message}",
                    extra={
                        "twilio_endpoint": endpoint,
                        "twilio_method": method,
                        "twilio_status_code": e.status_code,
                        "twilio_error": e.message,
                        "correlation_id": correlation_id
                    }
                )
                
                # Convert to Twilio-specific error
                details = e.details or {}
                details.update({
                    'service': 'twilio',
                    'endpoint': endpoint,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                raise TwilioAPIError(
                    f"Twilio API error: {e.message}",
                    details=details,
                    status_code=e.status_code or 502
                )


# Global HTTP client service instance
_http_client_service: Optional[HTTPClientService] = None


async def get_http_client_service() -> HTTPClientService:
    """
    Get the global HTTP client service instance.
    
    Returns:
        HTTPClientService: The HTTP client service instance
    """
    global _http_client_service
    if _http_client_service is None:
        _http_client_service = HTTPClientService()
    await _http_client_service._ensure_session()
    return _http_client_service


async def close_http_client_service():
    """Close the global HTTP client service."""
    global _http_client_service
    if _http_client_service:
        await _http_client_service.close()
        _http_client_service = None
"""
Custom exception classes for Ultravox-Twilio Integration Service.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone


class BaseServiceException(Exception):
    """Base exception class for all service errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "service_error",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        """
        Initialize base service exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            status_code: HTTP status code
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        self.timestamp = datetime.now(timezone.utc)
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class ConfigurationError(BaseServiceException):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="configuration_error",
            details=details,
            status_code=500
        )


class ValidationError(BaseServiceException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="validation_error",
            details=details,
            status_code=400
        )


class ExternalServiceError(BaseServiceException):
    """Exception raised for external service errors."""
    
    def __init__(
        self, 
        message: str, 
        service_name: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 502
    ):
        self.service_name = service_name
        details = details or {}
        details["service"] = service_name
        
        super().__init__(
            message=message,
            error_code="external_service_error",
            details=details,
            status_code=status_code
        )


class UltravoxAPIError(ExternalServiceError):
    """Exception raised for Ultravox API errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 502):
        super().__init__(
            message=message,
            service_name="ultravox",
            details=details,
            status_code=status_code
        )


class TwilioAPIError(ExternalServiceError):
    """Exception raised for Twilio API errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 502):
        super().__init__(
            message=message,
            service_name="twilio",
            details=details,
            status_code=status_code
        )


class NetworkError(BaseServiceException):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="network_error",
            details=details,
            status_code=503
        )


class RateLimitError(BaseServiceException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="rate_limit_exceeded",
            details=details,
            status_code=429
        )


class AuthenticationError(BaseServiceException):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="authentication_error",
            details=details,
            status_code=401
        )


class AuthorizationError(BaseServiceException):
    """Exception raised for authorization errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="authorization_error",
            details=details,
            status_code=403
        )


class ResourceNotFoundError(BaseServiceException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} '{resource_id}' not found"
        details = details or {}
        details.update({
            "resource_type": resource_type,
            "resource_id": resource_id
        })
        
        super().__init__(
            message=message,
            error_code="resource_not_found",
            details=details,
            status_code=404
        )


class BusinessLogicError(BaseServiceException):
    """Exception raised for business logic violations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="business_logic_error",
            details=details,
            status_code=422
        )


class TimeoutError(BaseServiceException):
    """Exception raised for timeout errors."""
    
    def __init__(self, operation: str, timeout_seconds: float, details: Optional[Dict[str, Any]] = None):
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        details = details or {}
        details.update({
            "operation": operation,
            "timeout_seconds": timeout_seconds
        })
        
        super().__init__(
            message=message,
            error_code="timeout_error",
            details=details,
            status_code=504
        )
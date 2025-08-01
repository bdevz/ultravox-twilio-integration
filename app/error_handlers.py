"""
Global exception handlers for FastAPI application.
"""

import logging
from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from app.exceptions import (
    BaseServiceException,
    ConfigurationError,
    ValidationError as CustomValidationError,
    ExternalServiceError,
    UltravoxAPIError,
    TwilioAPIError,
    NetworkError,
    RateLimitError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    BusinessLogicError,
    TimeoutError
)
from app.logging_config import get_correlation_id


logger = logging.getLogger(__name__)


async def base_service_exception_handler(request: Request, exc: BaseServiceException) -> JSONResponse:
    """
    Handle custom service exceptions.
    
    Args:
        request: FastAPI request object
        exc: Service exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = get_correlation_id()
    
    logger.error(
        f"Service exception: {exc.error_code}",
        extra={
            "error_code": exc.error_code,
            "error_message": exc.message,
            "details": exc.details,
            "status_code": exc.status_code,
            "path": str(request.url),
            "method": request.method,
            "correlation_id": correlation_id
        }
    )
    
    response_data = exc.to_dict()
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTP exceptions.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = get_correlation_id()
    
    logger.warning(
        f"HTTP exception: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url),
            "method": request.method,
            "correlation_id": correlation_id
        }
    )
    
    response_data = {
        "error": "http_error",
        "message": str(exc.detail),
        "status_code": exc.status_code
    }
    
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle Starlette HTTP exceptions.
    
    Args:
        request: FastAPI request object
        exc: Starlette HTTP exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = get_correlation_id()
    
    logger.warning(
        f"Starlette HTTP exception: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url),
            "method": request.method,
            "correlation_id": correlation_id
        }
    )
    
    response_data = {
        "error": "http_error",
        "message": str(exc.detail),
        "status_code": exc.status_code
    }
    
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors.
    
    Args:
        request: FastAPI request object
        exc: Validation error
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = get_correlation_id()
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    logger.warning(
        "Request validation failed",
        extra={
            "validation_errors": errors,
            "path": str(request.url),
            "method": request.method,
            "correlation_id": correlation_id
        }
    )
    
    response_data = {
        "error": "validation_error",
        "message": "Request validation failed",
        "details": {
            "validation_errors": errors
        }
    }
    
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=422,
        content=response_data
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    Args:
        request: FastAPI request object
        exc: Pydantic validation error
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = get_correlation_id()
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    logger.warning(
        "Pydantic validation failed",
        extra={
            "validation_errors": errors,
            "path": str(request.url),
            "method": request.method,
            "correlation_id": correlation_id
        }
    )
    
    response_data = {
        "error": "validation_error",
        "message": "Data validation failed",
        "details": {
            "validation_errors": errors
        }
    }
    
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=422,
        content=response_data
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.
    
    Args:
        request: FastAPI request object
        exc: Generic exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = get_correlation_id()
    
    logger.error(
        f"Unexpected exception: {type(exc).__name__}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_msg": str(exc),
            "path": str(request.url),
            "method": request.method,
            "correlation_id": correlation_id
        },
        exc_info=True
    )
    
    response_data = {
        "error": "internal_server_error",
        "message": "An unexpected error occurred. Please try again later.",
        "details": {
            "exception_type": type(exc).__name__
        }
    }
    
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=500,
        content=response_data
    )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Custom service exceptions
    app.add_exception_handler(BaseServiceException, base_service_exception_handler)
    app.add_exception_handler(ConfigurationError, base_service_exception_handler)
    app.add_exception_handler(CustomValidationError, base_service_exception_handler)
    app.add_exception_handler(ExternalServiceError, base_service_exception_handler)
    app.add_exception_handler(UltravoxAPIError, base_service_exception_handler)
    app.add_exception_handler(TwilioAPIError, base_service_exception_handler)
    app.add_exception_handler(NetworkError, base_service_exception_handler)
    app.add_exception_handler(RateLimitError, base_service_exception_handler)
    app.add_exception_handler(AuthenticationError, base_service_exception_handler)
    app.add_exception_handler(AuthorizationError, base_service_exception_handler)
    app.add_exception_handler(ResourceNotFoundError, base_service_exception_handler)
    app.add_exception_handler(BusinessLogicError, base_service_exception_handler)
    app.add_exception_handler(TimeoutError, base_service_exception_handler)
    
    # FastAPI and Starlette exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    
    # Validation exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    
    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered successfully")
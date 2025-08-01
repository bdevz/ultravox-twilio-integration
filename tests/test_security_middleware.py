"""
Tests for security middleware components.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware import (
    SecurityHeadersMiddleware,
    APIKeyValidationMiddleware,
    RateLimitingMiddleware,
    InputSanitizationMiddleware
)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""
    
    def test_security_headers_added(self):
        """Test that security headers are properly added to responses."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        # Check that security headers are present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
        
        # Check that server header is removed
        assert "server" not in response.headers
    
    def test_csp_header_content(self):
        """Test Content Security Policy header content."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "object-src 'none'" in csp
        assert "frame-src 'none'" in csp
    
    def test_hsts_header_https_only(self):
        """Test that HSTS header is only added for HTTPS requests."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # HTTP request should not have HSTS header
        response = client.get("/test")
        assert "Strict-Transport-Security" not in response.headers
        
        # Note: TestClient doesn't easily support HTTPS simulation
        # In a real deployment, HTTPS requests would get the HSTS header


class TestAPIKeyValidationMiddleware:
    """Test API key validation middleware."""
    
    @patch.dict('os.environ', {'VALID_API_KEYS': 'test-key'})
    def test_api_key_required_for_protected_paths(self):
        """Test that API key is required for protected paths."""
        app = FastAPI()
        app.add_middleware(
            APIKeyValidationMiddleware,
            required_for_paths=["/api/v1/"]
        )
        
        @app.get("/api/v1/test")
        async def protected_endpoint():
            return {"message": "protected"}
        
        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        client = TestClient(app)
        
        # Protected endpoint should require API key - expect exception to be raised
        with pytest.raises(Exception):  # HTTPException will be raised
            client.get("/api/v1/test")
        
        # Public endpoint should not require API key
        response = client.get("/public")
        assert response.status_code == 200
    
    @patch.dict('os.environ', {'VALID_API_KEYS': 'test-key-1,test-key-2'})
    def test_valid_api_key_accepted(self):
        """Test that valid API keys are accepted."""
        app = FastAPI()
        app.add_middleware(
            APIKeyValidationMiddleware,
            required_for_paths=["/api/v1/"]
        )
        
        @app.get("/api/v1/test")
        async def protected_endpoint():
            return {"message": "protected"}
        
        client = TestClient(app)
        
        # Valid API key should be accepted
        response = client.get(
            "/api/v1/test",
            headers={"X-API-Key": "test-key-1"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "protected"
    
    @patch.dict('os.environ', {'VALID_API_KEYS': 'test-key-1,test-key-2'})
    def test_invalid_api_key_rejected(self):
        """Test that invalid API keys are rejected."""
        app = FastAPI()
        app.add_middleware(
            APIKeyValidationMiddleware,
            required_for_paths=["/api/v1/"]
        )
        
        @app.get("/api/v1/test")
        async def protected_endpoint():
            return {"message": "protected"}
        
        client = TestClient(app)
        
        # Invalid API key should be rejected - expect exception to be raised
        with pytest.raises(Exception):  # HTTPException will be raised
            client.get(
                "/api/v1/test",
                headers={"X-API-Key": "invalid-key"}
            )
    
    def test_health_check_bypasses_api_key(self):
        """Test that health check endpoints bypass API key validation."""
        app = FastAPI()
        app.add_middleware(
            APIKeyValidationMiddleware,
            required_for_paths=["/api/v1/"]
        )
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        @app.get("/docs")
        async def docs_endpoint():
            return {"docs": "available"}
        
        client = TestClient(app)
        
        # Health and docs endpoints should not require API key
        response = client.get("/health")
        assert response.status_code == 200
        
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_no_api_keys_configured_development_mode(self):
        """Test that when no API keys are configured, validation is skipped (development mode)."""
        app = FastAPI()
        app.add_middleware(
            APIKeyValidationMiddleware,
            required_for_paths=["/api/v1/"]
        )
        
        @app.get("/api/v1/test")
        async def protected_endpoint():
            return {"message": "protected"}
        
        client = TestClient(app)
        
        # When no API keys are configured, requests should pass through
        response = client.get("/api/v1/test")
        assert response.status_code == 200
        assert response.json()["message"] == "protected"


class TestRateLimitingMiddleware:
    """Test rate limiting middleware."""
    
    def test_rate_limiting_allows_normal_requests(self):
        """Test that normal request rates are allowed."""
        app = FastAPI()
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=10,
            requests_per_hour=100,
            burst_limit=5
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Normal requests should be allowed
        for i in range(3):
            response = client.get("/test")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
    
    def test_burst_rate_limiting(self):
        """Test burst rate limiting functionality."""
        app = FastAPI()
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_limit=3  # Very low burst limit for testing
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # First few requests should succeed
        for i in range(3):
            response = client.get("/test")
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert response.json()["error"] == "rate_limit_exceeded"
        assert response.json()["limit_type"] == "burst"
        assert "Retry-After" in response.headers
    
    def test_health_check_bypasses_rate_limiting(self):
        """Test that health check endpoints bypass rate limiting."""
        app = FastAPI()
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=1,
            requests_per_hour=1,
            burst_limit=1
        )
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Health endpoint should not be rate limited
        for i in range(5):
            response = client.get("/health")
            assert response.status_code == 200
        
        # Regular endpoint should be rate limited after first request
        response = client.get("/test")
        assert response.status_code == 200
        
        response = client.get("/test")
        assert response.status_code == 429
    
    def test_rate_limit_headers(self):
        """Test that rate limit headers are properly set."""
        app = FastAPI()
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=10,
            requests_per_hour=100,
            burst_limit=5
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        response = client.get("/test")
        assert response.status_code == 200
        
        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        # Remaining should decrease with each request
        remaining1 = int(response.headers["X-RateLimit-Remaining"])
        
        response = client.get("/test")
        remaining2 = int(response.headers["X-RateLimit-Remaining"])
        
        assert remaining2 < remaining1


class TestInputSanitizationMiddleware:
    """Test input sanitization middleware."""
    
    def test_xss_sanitization(self):
        """Test XSS attack sanitization."""
        app = FastAPI()
        app.add_middleware(InputSanitizationMiddleware)
        
        @app.post("/test")
        async def test_endpoint(request: Request):
            body = await request.body()
            return json.loads(body.decode())
        
        client = TestClient(app)
        
        # Test XSS payload sanitization
        malicious_payload = {
            "name": "<script>alert('xss')</script>John",
            "description": "javascript:alert('xss')",
            "template_context": {
                "user_input": "<iframe src='evil.com'></iframe>Safe content"
            }
        }
        
        response = client.post("/test", json=malicious_payload)
        assert response.status_code == 200
        
        result = response.json()
        
        # Check that dangerous content is sanitized
        assert "<script>" not in result["name"]
        assert "javascript:" not in result["description"]
        assert "<iframe>" not in result["template_context"]["user_input"]
        
        # Check that safe content is preserved
        assert "John" in result["name"]
        assert "Safe content" in result["template_context"]["user_input"]
    
    def test_sql_injection_sanitization(self):
        """Test SQL injection attempt sanitization."""
        app = FastAPI()
        app.add_middleware(InputSanitizationMiddleware)
        
        @app.post("/test")
        async def test_endpoint(request: Request):
            body = await request.body()
            return json.loads(body.decode())
        
        client = TestClient(app)
        
        # Test SQL injection payload sanitization
        malicious_payload = {
            "query": "'; DROP TABLE users; --",
            "filter": "1=1 OR 1=1",
            "template_context": {
                "search": "admin' UNION SELECT * FROM passwords --"
            }
        }
        
        response = client.post("/test", json=malicious_payload)
        assert response.status_code == 200
        
        result = response.json()
        
        # Check that SQL injection patterns are filtered
        assert "DROP TABLE" not in result["query"]
        assert "[FILTERED]" in result["query"]
        assert "[FILTERED]" in result["filter"]
        assert "UNION SELECT" not in result["template_context"]["search"]
    
    def test_nested_object_sanitization(self):
        """Test sanitization of nested objects and arrays."""
        app = FastAPI()
        app.add_middleware(InputSanitizationMiddleware)
        
        @app.post("/test")
        async def test_endpoint(request: Request):
            body = await request.body()
            return json.loads(body.decode())
        
        client = TestClient(app)
        
        # Test nested structure sanitization
        payload = {
            "user": {
                "name": "<script>alert('nested')</script>Alice",
                "preferences": {
                    "theme": "javascript:void(0)",
                    "tags": [
                        "safe_tag",
                        "<script>alert('array')</script>dangerous_tag"
                    ]
                }
            },
            "items": [
                {"title": "Safe Title"},
                {"title": "<script>alert('item')</script>Unsafe Title"}
            ]
        }
        
        response = client.post("/test", json=payload)
        assert response.status_code == 200
        
        result = response.json()
        
        # Check nested sanitization
        assert "<script>" not in result["user"]["name"]
        assert "Alice" in result["user"]["name"]
        assert "javascript:" not in result["user"]["preferences"]["theme"]
        assert "<script>" not in result["user"]["preferences"]["tags"][1]
        assert "<script>" not in result["items"][1]["title"]
        assert "Unsafe Title" in result["items"][1]["title"]
    
    def test_non_json_requests_pass_through(self):
        """Test that non-JSON requests pass through without sanitization."""
        app = FastAPI()
        app.add_middleware(InputSanitizationMiddleware)
        
        @app.post("/test")
        async def test_endpoint(request: Request):
            body = await request.body()
            return {"received": body.decode()}
        
        client = TestClient(app)
        
        # Test form data (should pass through)
        response = client.post(
            "/test",
            data="name=<script>alert('test')</script>",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        # Original content should be preserved for non-JSON
        result = response.json()
        assert "<script>" in result["received"]
    
    def test_get_requests_not_sanitized(self):
        """Test that GET requests are not processed by sanitization middleware."""
        app = FastAPI()
        app.add_middleware(InputSanitizationMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # GET requests should pass through normally
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["message"] == "test"


class TestSecurityMiddlewareIntegration:
    """Test integration of multiple security middleware components."""
    
    @patch.dict('os.environ', {'VALID_API_KEYS': 'test-key'})
    def test_full_security_stack(self):
        """Test that all security middleware work together properly."""
        app = FastAPI()
        
        # Add all security middleware
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=10,
            requests_per_hour=100,
            burst_limit=5
        )
        app.add_middleware(
            APIKeyValidationMiddleware,
            required_for_paths=["/api/v1/"]
        )
        app.add_middleware(InputSanitizationMiddleware)
        
        @app.post("/api/v1/test")
        async def protected_endpoint(request: Request):
            body = await request.body()
            return json.loads(body.decode())
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        client = TestClient(app)
        
        # Test that health endpoint works without API key
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers  # Security headers applied
        
        # Test that protected endpoint requires API key - expect exception
        with pytest.raises(Exception):  # HTTPException will be raised
            client.post("/api/v1/test", json={"test": "data"})
        
        # Test successful request with API key and input sanitization
        malicious_payload = {
            "name": "<script>alert('test')</script>John",
            "template_context": {
                "message": "Hello World"
            }
        }
        
        response = client.post(
            "/api/v1/test",
            json=malicious_payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        
        # Check that input was sanitized
        result = response.json()
        assert "<script>" not in result["name"]
        assert "John" in result["name"]
        
        # Check that security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-RateLimit-Limit" in response.headers
    
    def test_middleware_order_matters(self):
        """Test that middleware order affects behavior correctly."""
        # This test ensures that our middleware stack is ordered correctly
        # in the main application
        
        app = FastAPI()
        
        # Add middleware in the same order as main.py
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=2,  # Low limit for testing
            burst_limit=1
        )
        app.add_middleware(InputSanitizationMiddleware)
        
        @app.post("/test")
        async def test_endpoint(request: Request):
            body = await request.body()
            return json.loads(body.decode())
        
        client = TestClient(app)
        
        # First request should succeed with sanitization
        response = client.post("/test", json={"data": "<script>test</script>"})
        assert response.status_code == 200
        assert "<script>" not in response.json()["data"]
        assert "X-Content-Type-Options" in response.headers
        
        # Second request should be rate limited before sanitization
        response = client.post("/test", json={"data": "<script>test</script>"})
        assert response.status_code == 429
        assert response.json()["error"] == "rate_limit_exceeded"
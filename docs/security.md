# Security Best Practices Implementation

This document describes the security features implemented in the Ultravox-Twilio Integration Service.

## Overview

The application implements multiple layers of security middleware to protect against common web application vulnerabilities and attacks:

1. **Security Headers Middleware** - Adds comprehensive security headers
2. **API Key Validation Middleware** - Validates API keys for protected endpoints
3. **Rate Limiting Middleware** - Prevents abuse through rate limiting
4. **Input Sanitization Middleware** - Sanitizes user input to prevent XSS and injection attacks

## Security Headers

The `SecurityHeadersMiddleware` adds the following security headers to all responses:

### Standard Security Headers
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking attacks
- `X-XSS-Protection: 1; mode=block` - Enables XSS filtering
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information

### Content Security Policy (CSP)
A comprehensive CSP header that:
- Restricts script sources to self and inline (for API docs)
- Restricts style sources to self and inline (for API docs)
- Allows data URIs for images
- Disables plugins and frames
- Restricts form submissions to self

### HTTPS Security
- `Strict-Transport-Security` header (HSTS) for HTTPS connections
- Includes subdomains and preload directives

### Permissions Policy
Restricts access to browser features:
- Disables geolocation, microphone, camera access
- Disables payment, USB, and sensor APIs
- Allows fullscreen for self only

## API Key Validation

The `APIKeyValidationMiddleware` provides secure API key authentication:

### Configuration
```bash
# Production: Comma-separated list of valid API keys
VALID_API_KEYS=key1,key2,key3

# Development: Single development key (fallback)
DEV_API_KEY=dev-key-12345
```

### Protected Endpoints
By default, the following endpoints require API key validation:
- `/api/v1/agents/*` - All agent management endpoints
- `/api/v1/calls/*` - All call initiation endpoints

### Bypassed Endpoints
These endpoints do not require API keys:
- `/health` - Health check endpoints
- `/docs` - API documentation
- `/redoc` - Alternative API documentation
- `/openapi.json` - OpenAPI specification

### Usage
Include the API key in the `X-API-Key` header:
```bash
curl -H "X-API-Key: your-api-key" https://api.example.com/api/v1/agents
```

### Development Mode
When no API keys are configured, validation is skipped and a warning is logged. This allows for easy development but should never be used in production.

## Rate Limiting

The `RateLimitingMiddleware` implements multiple rate limiting strategies:

### Rate Limits
- **Burst Limit**: 10 requests in 10 seconds (configurable)
- **Per Minute**: 60 requests per minute (configurable)
- **Per Hour**: 1000 requests per hour (configurable)

### Configuration
```bash
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_BURST=10
```

### Rate Limit Headers
Successful responses include rate limit information:
- `X-RateLimit-Limit` - Current rate limit
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Reset timestamp

### Rate Limit Exceeded Response
When rate limits are exceeded, a 429 status code is returned with:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded: too many requests per minute",
  "limit_type": "minute",
  "retry_after": 60
}
```

### Bypassed Endpoints
Rate limiting is bypassed for:
- `/health` - Health check endpoints
- `/docs` - API documentation
- `/redoc` - Alternative API documentation
- `/openapi.json` - OpenAPI specification

## Input Sanitization

The `InputSanitizationMiddleware` protects against XSS and injection attacks:

### XSS Protection
Automatically sanitizes dangerous HTML/JavaScript content:
- Removes `<script>` tags
- Removes `javascript:` URLs
- Removes event handlers (`onclick`, etc.)
- Removes dangerous HTML elements (`<iframe>`, `<object>`, etc.)
- HTML-encodes remaining content

### SQL Injection Protection
Detects and filters potential SQL injection patterns:
- SQL keywords (`UNION`, `SELECT`, `DROP`, etc.)
- SQL comment patterns (`--`, `/*`, `*/`)
- Boolean-based injection patterns

### Template Context Sanitization
Special attention is paid to `template_context` fields in API requests, as these are often used in dynamic content generation.

### Nested Object Support
Recursively sanitizes:
- Nested objects and dictionaries
- Arrays and lists
- Mixed data structures

### Example
Input:
```json
{
  "name": "<script>alert('xss')</script>John",
  "template_context": {
    "message": "Hello'; DROP TABLE users; --"
  }
}
```

Sanitized output:
```json
{
  "name": "John",
  "template_context": {
    "message": "Hello[FILTERED]"
  }
}
```

## Security Configuration

### Environment Variables
Create a `.env` file based on `.env.security.example`:

```bash
# Copy the example file
cp .env.security.example .env

# Edit with your values
vim .env
```

### Required Configuration
For production deployment, ensure these are configured:
- `VALID_API_KEYS` - List of valid API keys
- `RATE_LIMIT_*` - Appropriate rate limits for your use case
- `MAX_CONTENT_LENGTH` - Maximum request size
- `CORS_ORIGINS` - Allowed origins for CORS

### Optional Configuration
- `DEV_API_KEY` - Development API key (development only)
- `LOG_REQUEST_BODY` - Log request bodies (debugging only)
- `LOG_RESPONSE_BODY` - Log response bodies (debugging only)

## Monitoring and Logging

### Security Events
All security-related events are logged with appropriate levels:
- **INFO**: Successful API key validation
- **WARNING**: Rate limit exceeded, invalid API keys, suspicious input
- **ERROR**: Security middleware failures

### Correlation IDs
All requests include correlation IDs for tracking security events across the application.

### Metrics
Security metrics are collected for:
- Rate limit violations per IP
- API key validation failures
- Input sanitization events
- Security header application

## Best Practices

### API Key Management
1. Use strong, randomly generated API keys
2. Rotate API keys regularly
3. Use different keys for different environments
4. Never log API keys in plain text
5. Store keys securely (environment variables, secrets management)

### Rate Limiting
1. Set appropriate limits based on expected usage
2. Monitor rate limit violations
3. Consider different limits for different endpoints
4. Implement graceful degradation for rate-limited clients

### Input Validation
1. Validate all input at the application boundary
2. Use allowlists rather than blocklists when possible
3. Sanitize data before storage and display
4. Log suspicious input patterns

### Monitoring
1. Monitor security logs regularly
2. Set up alerts for security events
3. Track security metrics over time
4. Implement automated responses to attacks

## Testing Security Features

Run the security middleware tests:
```bash
python -m pytest tests/test_security_middleware.py -v
```

Test specific middleware:
```bash
# Test API key validation
python -m pytest tests/test_security_middleware.py::TestAPIKeyValidationMiddleware -v

# Test rate limiting
python -m pytest tests/test_security_middleware.py::TestRateLimitingMiddleware -v

# Test input sanitization
python -m pytest tests/test_security_middleware.py::TestInputSanitizationMiddleware -v
```

## Security Considerations

### Known Limitations
1. Rate limiting is in-memory only (resets on restart)
2. API keys are stored in environment variables (consider secrets management)
3. Input sanitization may be overly aggressive for some use cases

### Future Enhancements
1. Persistent rate limiting with Redis
2. JWT-based authentication
3. Role-based access control
4. Advanced threat detection
5. Security audit logging

## Compliance

This implementation helps meet security requirements for:
- **OWASP Top 10** - Addresses injection, XSS, security misconfiguration
- **PCI DSS** - Secure transmission and input validation
- **SOC 2** - Security controls and monitoring
- **GDPR** - Data protection through input validation and logging controls
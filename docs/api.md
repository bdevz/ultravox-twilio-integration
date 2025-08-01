# Ultravox-Twilio Integration API Documentation

## Overview

The Ultravox-Twilio Integration Service provides a REST API for creating and managing Ultravox AI agents with Twilio voice integration. This service acts as a bridge between Ultravox's AI capabilities and Twilio's telecommunications infrastructure, enabling developers to create voice-enabled AI applications.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All API endpoints (except health checks) require API key authentication via the `X-API-Key` header:

```http
X-API-Key: your-api-key-here
```

## Content Type

All requests and responses use JSON format:

```http
Content-Type: application/json
```

## Rate Limiting

The API implements rate limiting with the following default limits:
- 60 requests per minute
- 1000 requests per hour
- Burst limit of 10 requests

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "error_type",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional error details"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "correlation-id"
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

## Endpoints

### Agent Management

#### Create Agent

Create a new Ultravox agent with specified configuration.

```http
POST /api/v1/agents
```

**Request Body:**

```json
{
  "name": "Customer Support Agent",
  "prompt": "You are a helpful customer support agent. Be polite and professional.",
  "voice": "default",
  "language": "en",
  "template_variables": {
    "company_name": "Acme Corp",
    "support_hours": "9 AM - 5 PM EST"
  }
}
```

**Response (201 Created):**

```json
{
  "id": "agent_123456",
  "config": {
    "name": "Customer Support Agent",
    "prompt": "You are a helpful customer support agent. Be polite and professional.",
    "voice": "default",
    "language": "en",
    "template_variables": {
      "company_name": "Acme Corp",
      "support_hours": "9 AM - 5 PM EST"
    }
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "status": "active"
}
```

#### List Agents

Retrieve a list of all agents with optional pagination.

```http
GET /api/v1/agents?limit=10&offset=0
```

**Query Parameters:**
- `limit` (optional): Maximum number of agents to return (default: no limit)
- `offset` (optional): Number of agents to skip (default: 0)

**Response (200 OK):**

```json
[
  {
    "id": "agent_123456",
    "config": {
      "name": "Customer Support Agent",
      "prompt": "You are a helpful customer support agent.",
      "voice": "default",
      "language": "en",
      "template_variables": {}
    },
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "status": "active"
  }
]
```

#### Get Agent

Retrieve details for a specific agent.

```http
GET /api/v1/agents/{agent_id}
```

**Path Parameters:**
- `agent_id`: Unique identifier for the agent

**Response (200 OK):**

```json
{
  "id": "agent_123456",
  "config": {
    "name": "Customer Support Agent",
    "prompt": "You are a helpful customer support agent.",
    "voice": "default",
    "language": "en",
    "template_variables": {}
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "status": "active"
}
```

#### Update Agent

Update an existing agent's configuration.

```http
PUT /api/v1/agents/{agent_id}
```

**Path Parameters:**
- `agent_id`: Unique identifier for the agent

**Request Body:**

```json
{
  "name": "Updated Customer Support Agent",
  "prompt": "You are an updated helpful customer support agent.",
  "voice": "default",
  "language": "en",
  "template_variables": {
    "company_name": "Updated Acme Corp"
  }
}
```

**Response (200 OK):**

```json
{
  "id": "agent_123456",
  "config": {
    "name": "Updated Customer Support Agent",
    "prompt": "You are an updated helpful customer support agent.",
    "voice": "default",
    "language": "en",
    "template_variables": {
      "company_name": "Updated Acme Corp"
    }
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:30:00Z",
  "status": "active"
}
```

### Call Management

#### Initiate Call

Start a voice call using a specific agent.

```http
POST /api/v1/calls/{agent_id}
```

**Path Parameters:**
- `agent_id`: Unique identifier for the agent to use

**Request Body:**

```json
{
  "phone_number": "+1234567890",
  "template_context": {
    "customer_name": "John Doe",
    "order_id": "ORD-12345",
    "issue_type": "billing"
  },
  "agent_id": "agent_123456"
}
```

**Response (201 Created):**

```json
{
  "call_sid": "CA1234567890abcdef1234567890abcdef",
  "join_url": "wss://api.ultravox.ai/calls/call_789/join",
  "status": "initiated",
  "created_at": "2024-01-01T12:00:00Z",
  "agent_id": "agent_123456",
  "phone_number": "+1234567890"
}
```

### Health and Monitoring

#### Basic Health Check

Check if the service is running and configured properly.

```http
GET /api/v1/health
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "service": "ultravox-twilio-integration",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime": {
    "startup_complete": true,
    "config_validated": true,
    "ongoing_calls": 2
  },
  "checks": {
    "configuration": "ok",
    "ultravox_config": "ok",
    "twilio_config": "ok"
  }
}
```

#### Detailed Health Check

Comprehensive health check including external service connectivity.

```http
GET /api/v1/health/detailed
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "service": "ultravox-twilio-integration",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime": {
    "startup_complete": true,
    "config_validated": true,
    "ongoing_calls": 2
  },
  "checks": {
    "configuration": "ok",
    "ultravox_config": "ok",
    "twilio_config": "ok",
    "ultravox_api": "ok",
    "twilio_api": "ok"
  }
}
```

### Metrics

#### Get Application Metrics

Retrieve application performance metrics.

```http
GET /api/v1/metrics
```

**Response (200 OK):**

```json
{
  "requests": {
    "total": 1250,
    "success": 1200,
    "errors": 50
  },
  "calls": {
    "total": 45,
    "successful": 42,
    "failed": 3
  },
  "agents": {
    "total": 5,
    "active": 5
  },
  "response_times": {
    "avg_ms": 150,
    "p95_ms": 300,
    "p99_ms": 500
  }
}
```

#### Get Recent Events

Retrieve recent metric events.

```http
GET /api/v1/metrics/events?limit=100
```

**Query Parameters:**
- `limit` (optional): Maximum number of events to return (default: 100, max: 1000)

**Response (200 OK):**

```json
{
  "events": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "type": "call_initiated",
      "agent_id": "agent_123456",
      "call_sid": "CA1234567890abcdef1234567890abcdef"
    }
  ],
  "count": 1,
  "limit": 100
}
```

#### Get Recent API Calls

Retrieve recent API call metrics.

```http
GET /api/v1/metrics/api-calls?limit=100
```

**Query Parameters:**
- `limit` (optional): Maximum number of API calls to return (default: 100, max: 1000)

**Response (200 OK):**

```json
{
  "api_calls": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "method": "POST",
      "endpoint": "/api/v1/calls/agent_123456",
      "status_code": 201,
      "response_time_ms": 150
    }
  ],
  "count": 1,
  "limit": 100
}
```

## Data Models

### Agent Configuration

```json
{
  "name": "string (1-100 chars, letters/numbers/spaces/hyphens/underscores)",
  "prompt": "string (1-10000 chars)",
  "voice": "string (optional, default: 'default')",
  "language": "string (optional, format: 'en' or 'en-US', default: 'en')",
  "template_variables": {
    "key": "string (valid identifier, max 100 chars)",
    "value": "string (max 1000 chars)"
  }
}
```

### Call Request

```json
{
  "phone_number": "string (international format: +[country][number])",
  "template_context": {
    "key": "any (string/number/boolean/array/object, max 50 variables)"
  },
  "agent_id": "string (letters/numbers/hyphens/underscores)"
}
```

### Agent Status Values

- `active`: Agent is ready for calls
- `inactive`: Agent is disabled
- `creating`: Agent is being created
- `error`: Agent creation or update failed

### Call Status Values

- `initiated`: Call has been started
- `ringing`: Phone is ringing
- `in-progress`: Call is active
- `completed`: Call ended successfully
- `failed`: Call failed to connect
- `busy`: Called number was busy
- `no-answer`: No one answered the call
- `canceled`: Call was canceled

## Validation Rules

### Phone Numbers

- Must be in international format starting with `+`
- Must include country code (1-3 digits)
- Total length: 8-18 characters including `+`
- Examples: `+1234567890`, `+441234567890`, `+33123456789`

### Agent Names

- 1-100 characters
- Letters, numbers, spaces, hyphens, underscores only
- Cannot be empty or whitespace only

### Template Variables

- Keys must be valid identifiers (letters, numbers, underscore)
- Keys cannot start with numbers
- Maximum 50 variables per context
- String values limited to 1000 characters
- Reserved keys: `agent_id`, `call_id`, `timestamp`, `system`, `internal`

### API Keys

- 10-200 characters
- Cannot be empty or whitespace only
- Must be provided in `X-API-Key` header

## OpenAPI/Swagger Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

These interfaces provide:
- Interactive API testing
- Complete schema documentation
- Request/response examples
- Authentication testing
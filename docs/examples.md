# API Usage Examples

This document provides comprehensive examples for using the Ultravox-Twilio Integration API.

## Prerequisites

Before using the API, ensure you have:
1. A running instance of the service
2. Valid API key configured
3. Ultravox API credentials
4. Twilio account credentials

## Authentication

All examples assume you have an API key. Include it in all requests:

```bash
export API_KEY="your-api-key-here"
export BASE_URL="http://localhost:8000/api/v1"
```

## Agent Management Examples

### Example 1: Create a Simple Customer Support Agent

```bash
curl -X POST "$BASE_URL/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Customer Support Agent",
    "prompt": "You are a helpful customer support agent for Acme Corp. Be polite, professional, and try to resolve customer issues efficiently.",
    "voice": "default",
    "language": "en"
  }'
```

**Response:**
```json
{
  "id": "agent_cs_001",
  "config": {
    "name": "Customer Support Agent",
    "prompt": "You are a helpful customer support agent for Acme Corp. Be polite, professional, and try to resolve customer issues efficiently.",
    "voice": "default",
    "language": "en",
    "template_variables": {}
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "status": "active"
}
```

### Example 2: Create an Agent with Template Variables

```bash
curl -X POST "$BASE_URL/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Sales Agent",
    "prompt": "You are a sales agent for {{company_name}}. Your goal is to help customers understand our products and services. Our business hours are {{business_hours}}. Be enthusiastic but not pushy.",
    "voice": "default",
    "language": "en",
    "template_variables": {
      "company_name": "TechCorp Solutions",
      "business_hours": "Monday-Friday 9AM-6PM EST",
      "contact_email": "sales@techcorp.com"
    }
  }'
```

**Response:**
```json
{
  "id": "agent_sales_001",
  "config": {
    "name": "Sales Agent",
    "prompt": "You are a sales agent for {{company_name}}. Your goal is to help customers understand our products and services. Our business hours are {{business_hours}}. Be enthusiastic but not pushy.",
    "voice": "default",
    "language": "en",
    "template_variables": {
      "company_name": "TechCorp Solutions",
      "business_hours": "Monday-Friday 9AM-6PM EST",
      "contact_email": "sales@techcorp.com"
    }
  },
  "created_at": "2024-01-01T12:05:00Z",
  "updated_at": "2024-01-01T12:05:00Z",
  "status": "active"
}
```

### Example 3: List All Agents

```bash
curl -X GET "$BASE_URL/agents" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
[
  {
    "id": "agent_cs_001",
    "config": {
      "name": "Customer Support Agent",
      "prompt": "You are a helpful customer support agent...",
      "voice": "default",
      "language": "en",
      "template_variables": {}
    },
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "status": "active"
  },
  {
    "id": "agent_sales_001",
    "config": {
      "name": "Sales Agent",
      "prompt": "You are a sales agent for {{company_name}}...",
      "voice": "default",
      "language": "en",
      "template_variables": {
        "company_name": "TechCorp Solutions",
        "business_hours": "Monday-Friday 9AM-6PM EST",
        "contact_email": "sales@techcorp.com"
      }
    },
    "created_at": "2024-01-01T12:05:00Z",
    "updated_at": "2024-01-01T12:05:00Z",
    "status": "active"
  }
]
```

### Example 4: List Agents with Pagination

```bash
curl -X GET "$BASE_URL/agents?limit=5&offset=0" \
  -H "X-API-Key: $API_KEY"
```

### Example 5: Get Specific Agent

```bash
curl -X GET "$BASE_URL/agents/agent_cs_001" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "id": "agent_cs_001",
  "config": {
    "name": "Customer Support Agent",
    "prompt": "You are a helpful customer support agent for Acme Corp. Be polite, professional, and try to resolve customer issues efficiently.",
    "voice": "default",
    "language": "en",
    "template_variables": {}
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "status": "active"
}
```

### Example 6: Update Agent Configuration

```bash
curl -X PUT "$BASE_URL/agents/agent_cs_001" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Enhanced Customer Support Agent",
    "prompt": "You are an enhanced customer support agent for Acme Corp. Be polite, professional, and try to resolve customer issues efficiently. You can also help with basic technical troubleshooting.",
    "voice": "default",
    "language": "en",
    "template_variables": {
      "support_email": "support@acme.com",
      "escalation_number": "+1-800-ACME-HELP"
    }
  }'
```

**Response:**
```json
{
  "id": "agent_cs_001",
  "config": {
    "name": "Enhanced Customer Support Agent",
    "prompt": "You are an enhanced customer support agent for Acme Corp. Be polite, professional, and try to resolve customer issues efficiently. You can also help with basic technical troubleshooting.",
    "voice": "default",
    "language": "en",
    "template_variables": {
      "support_email": "support@acme.com",
      "escalation_number": "+1-800-ACME-HELP"
    }
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:30:00Z",
  "status": "active"
}
```

## Call Management Examples

### Example 7: Simple Call Initiation

```bash
curl -X POST "$BASE_URL/calls/agent_cs_001" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "phone_number": "+1234567890",
    "template_context": {},
    "agent_id": "agent_cs_001"
  }'
```

**Response:**
```json
{
  "call_sid": "CA1234567890abcdef1234567890abcdef",
  "join_url": "wss://api.ultravox.ai/calls/call_789/join",
  "status": "initiated",
  "created_at": "2024-01-01T12:00:00Z",
  "agent_id": "agent_cs_001",
  "phone_number": "+1234567890"
}
```

### Example 8: Call with Template Context

```bash
curl -X POST "$BASE_URL/calls/agent_sales_001" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "phone_number": "+1987654321",
    "template_context": {
      "customer_name": "John Smith",
      "product_interest": "Enterprise Software",
      "lead_source": "Website Contact Form",
      "priority": "high",
      "previous_contact": false
    },
    "agent_id": "agent_sales_001"
  }'
```

**Response:**
```json
{
  "call_sid": "CA9876543210fedcba9876543210fedcba",
  "join_url": "wss://api.ultravox.ai/calls/call_456/join",
  "status": "initiated",
  "created_at": "2024-01-01T12:15:00Z",
  "agent_id": "agent_sales_001",
  "phone_number": "+1987654321"
}
```

### Example 9: International Call

```bash
curl -X POST "$BASE_URL/calls/agent_cs_001" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "phone_number": "+441234567890",
    "template_context": {
      "customer_name": "Emma Johnson",
      "timezone": "GMT",
      "language_preference": "English",
      "account_type": "Premium"
    },
    "agent_id": "agent_cs_001"
  }'
```

## Health Check Examples

### Example 10: Basic Health Check

```bash
curl -X GET "$BASE_URL/health"
```

**Response:**
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

### Example 11: Detailed Health Check

```bash
curl -X GET "$BASE_URL/health/detailed"
```

**Response:**
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

## Metrics Examples

### Example 12: Get Application Metrics

```bash
curl -X GET "$BASE_URL/metrics" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
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

### Example 13: Get Recent Events

```bash
curl -X GET "$BASE_URL/metrics/events?limit=10" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "events": [
    {
      "timestamp": "2024-01-01T12:15:00Z",
      "type": "call_completed",
      "agent_id": "agent_cs_001",
      "call_sid": "CA1234567890abcdef1234567890abcdef",
      "duration_seconds": 180
    },
    {
      "timestamp": "2024-01-01T12:10:00Z",
      "type": "call_initiated",
      "agent_id": "agent_sales_001",
      "call_sid": "CA9876543210fedcba9876543210fedcba"
    }
  ],
  "count": 2,
  "limit": 10
}
```

### Example 14: Get Recent API Calls

```bash
curl -X GET "$BASE_URL/metrics/api-calls?limit=5" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "api_calls": [
    {
      "timestamp": "2024-01-01T12:15:00Z",
      "method": "POST",
      "endpoint": "/api/v1/calls/agent_sales_001",
      "status_code": 201,
      "response_time_ms": 145
    },
    {
      "timestamp": "2024-01-01T12:10:00Z",
      "method": "GET",
      "endpoint": "/api/v1/agents",
      "status_code": 200,
      "response_time_ms": 25
    }
  ],
  "count": 2,
  "limit": 5
}
```

## Error Handling Examples

### Example 15: Invalid Phone Number

```bash
curl -X POST "$BASE_URL/calls/agent_cs_001" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "phone_number": "invalid-number",
    "template_context": {},
    "agent_id": "agent_cs_001"
  }'
```

**Response (400 Bad Request):**
```json
{
  "error": "validation_error",
  "message": "Phone number must be in valid international format (+[country code][number], 7-18 digits total)",
  "details": {
    "field": "phone_number",
    "value": "invalid-number"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### Example 16: Agent Not Found

```bash
curl -X GET "$BASE_URL/agents/nonexistent_agent" \
  -H "X-API-Key: $API_KEY"
```

**Response (404 Not Found):**
```json
{
  "error": "agent_not_found",
  "message": "Agent with ID 'nonexistent_agent' not found",
  "details": {
    "agent_id": "nonexistent_agent"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_789012"
}
```

### Example 17: Missing API Key

```bash
curl -X GET "$BASE_URL/agents"
```

**Response (401 Unauthorized):**
```json
{
  "error": "unauthorized",
  "message": "API key is required",
  "details": {
    "header": "X-API-Key"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_345678"
}
```

### Example 18: Rate Limit Exceeded

```bash
# After making too many requests quickly
curl -X GET "$BASE_URL/agents" \
  -H "X-API-Key: $API_KEY"
```

**Response (429 Too Many Requests):**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please try again later.",
  "details": {
    "limit": 60,
    "window": "1 minute",
    "retry_after": 30
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_901234"
}
```

## Advanced Usage Examples

### Example 19: Creating Multiple Agents for Different Use Cases

```bash
# Create a technical support agent
curl -X POST "$BASE_URL/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Technical Support Agent",
    "prompt": "You are a technical support specialist. Help users troubleshoot technical issues with {{product_name}}. Be patient and provide step-by-step instructions.",
    "voice": "default",
    "language": "en",
    "template_variables": {
      "product_name": "CloudSync Pro",
      "support_portal": "https://support.cloudsync.com",
      "escalation_team": "Level 2 Support"
    }
  }'

# Create a billing support agent
curl -X POST "$BASE_URL/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Billing Support Agent",
    "prompt": "You are a billing support specialist. Help customers with billing questions, payment issues, and account management for {{company_name}}.",
    "voice": "default",
    "language": "en",
    "template_variables": {
      "company_name": "CloudSync Inc",
      "billing_email": "billing@cloudsync.com",
      "payment_methods": "Credit Card, PayPal, Bank Transfer"
    }
  }'
```

### Example 20: Batch Call Initiation

```bash
# Script to initiate multiple calls
#!/bin/bash

AGENT_ID="agent_cs_001"
PHONE_NUMBERS=("+1234567890" "+1987654321" "+1555123456")

for phone in "${PHONE_NUMBERS[@]}"; do
  echo "Initiating call to $phone"
  curl -X POST "$BASE_URL/calls/$AGENT_ID" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d "{
      \"phone_number\": \"$phone\",
      \"template_context\": {
        \"campaign\": \"Product Launch\",
        \"priority\": \"normal\"
      },
      \"agent_id\": \"$AGENT_ID\"
    }"
  echo ""
  sleep 1  # Rate limiting consideration
done
```

## Python SDK Example

Here's how you might use the API with Python:

```python
import requests
import json
from typing import Dict, Any, Optional

class UltravoxTwilioClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        })
    
    def create_agent(self, name: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Create a new agent."""
        data = {
            'name': name,
            'prompt': prompt,
            **kwargs
        }
        response = self.session.post(f'{self.base_url}/agents', json=data)
        response.raise_for_status()
        return response.json()
    
    def list_agents(self, limit: Optional[int] = None, offset: Optional[int] = None) -> list:
        """List all agents."""
        params = {}
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset
        
        response = self.session.get(f'{self.base_url}/agents', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent by ID."""
        response = self.session.get(f'{self.base_url}/agents/{agent_id}')
        response.raise_for_status()
        return response.json()
    
    def initiate_call(self, agent_id: str, phone_number: str, 
                     template_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initiate a call."""
        data = {
            'phone_number': phone_number,
            'template_context': template_context or {},
            'agent_id': agent_id
        }
        response = self.session.post(f'{self.base_url}/calls/{agent_id}', json=data)
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        response = self.session.get(f'{self.base_url}/health')
        response.raise_for_status()
        return response.json()

# Usage example
client = UltravoxTwilioClient('http://localhost:8000/api/v1', 'your-api-key')

# Create an agent
agent = client.create_agent(
    name='Customer Service Bot',
    prompt='You are a helpful customer service agent.',
    template_variables={'company': 'Acme Corp'}
)

# Initiate a call
call_result = client.initiate_call(
    agent_id=agent['id'],
    phone_number='+1234567890',
    template_context={'customer_name': 'John Doe'}
)

print(f"Call initiated: {call_result['call_sid']}")
```

## JavaScript/Node.js Example

```javascript
class UltravoxTwilioClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
    }

    async request(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': this.apiKey
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(`API Error: ${error.message}`);
        }

        return response.json();
    }

    async createAgent(config) {
        return this.request('POST', '/agents', config);
    }

    async listAgents(limit = null, offset = null) {
        const params = new URLSearchParams();
        if (limit !== null) params.append('limit', limit);
        if (offset !== null) params.append('offset', offset);
        
        const query = params.toString();
        const endpoint = query ? `/agents?${query}` : '/agents';
        
        return this.request('GET', endpoint);
    }

    async initiateCall(agentId, phoneNumber, templateContext = {}) {
        return this.request('POST', `/calls/${agentId}`, {
            phone_number: phoneNumber,
            template_context: templateContext,
            agent_id: agentId
        });
    }

    async healthCheck() {
        return this.request('GET', '/health');
    }
}

// Usage example
const client = new UltravoxTwilioClient('http://localhost:8000/api/v1', 'your-api-key');

async function example() {
    try {
        // Create an agent
        const agent = await client.createAgent({
            name: 'Sales Assistant',
            prompt: 'You are a friendly sales assistant.',
            template_variables: { company: 'TechCorp' }
        });

        // Initiate a call
        const callResult = await client.initiateCall(
            agent.id,
            '+1234567890',
            { customer_name: 'Jane Smith', product: 'Enterprise Plan' }
        );

        console.log('Call initiated:', callResult.call_sid);
    } catch (error) {
        console.error('Error:', error.message);
    }
}

example();
```

These examples demonstrate the full range of API functionality and provide practical templates for integration into various applications and workflows.
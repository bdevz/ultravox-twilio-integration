# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Ultravox-Twilio Integration Service.

## Quick Diagnostics

### Health Check Commands

Start troubleshooting by checking the service health:

```bash
# Basic health check
curl -X GET "http://localhost:8000/api/v1/health"

# Detailed health check with external service connectivity
curl -X GET "http://localhost:8000/api/v1/health/detailed"
```

### Log Analysis

Check the application logs for detailed error information:

```bash
# If running with Docker
docker logs ultravox-twilio-service

# If running directly
tail -f /path/to/logfile.log

# Check for specific error patterns
grep -i "error\|exception\|failed" /path/to/logfile.log
```

## Common Issues and Solutions

### 1. Service Won't Start

#### Symptoms
- Service fails to start
- Health check returns 503 Service Unavailable
- Startup errors in logs

#### Possible Causes and Solutions

**Missing Environment Variables**
```bash
# Check if required environment variables are set
echo $ULTRAVOX_API_KEY
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN
echo $TWILIO_PHONE_NUMBER
```

**Solution:**
```bash
# Set required environment variables
export ULTRAVOX_API_KEY="your-ultravox-api-key"
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your-twilio-auth-token"
export TWILIO_PHONE_NUMBER="+1234567890"
export API_KEY="your-service-api-key"
```

**Invalid Configuration Format**
- Check that Twilio Account SID starts with "AC" followed by 32 hex characters
- Verify Twilio Auth Token is 32 hex characters
- Ensure phone numbers are in international format (+1234567890)
- Confirm Ultravox API key is valid and not expired

**Port Already in Use**
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill process using the port
kill -9 <PID>

# Or use a different port
export PORT=8001
```

### 2. Authentication Issues

#### Symptoms
- 401 Unauthorized responses
- "API key is required" errors
- "Invalid API key" messages

#### Solutions

**Missing API Key Header**
```bash
# Ensure X-API-Key header is included
curl -X GET "http://localhost:8000/api/v1/agents" \
  -H "X-API-Key: your-api-key-here"
```

**Invalid API Key**
- Verify the API key is correctly configured in environment variables
- Check for extra spaces or newlines in the API key
- Ensure the API key hasn't expired or been revoked

**Case Sensitivity**
- Header name must be exactly "X-API-Key" (case-sensitive)
- API key values are case-sensitive

### 3. Agent Creation Failures

#### Symptoms
- 400 Bad Request when creating agents
- "Agent creation failed" errors
- Validation errors on agent configuration

#### Common Validation Issues

**Invalid Agent Name**
```json
{
  "error": "validation_error",
  "message": "Agent name can only contain letters, numbers, spaces, hyphens, and underscores"
}
```

**Solution:**
```bash
# Valid agent name examples
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Customer-Support_Agent_01",
    "prompt": "You are a helpful assistant."
  }'
```

**Prompt Too Long**
```json
{
  "error": "validation_error",
  "message": "Prompt must be between 1 and 10000 characters"
}
```

**Invalid Template Variables**
```json
{
  "error": "validation_error",
  "message": "Template variable key \"123invalid\" must be a valid identifier"
}
```

**Solution:**
```bash
# Valid template variables
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Support Agent",
    "prompt": "Hello {{customer_name}}, how can I help?",
    "template_variables": {
      "customer_name": "valued customer",
      "company_name": "Acme Corp",
      "support_hours": "9 AM - 5 PM"
    }
  }'
```

### 4. Call Initiation Problems

#### Symptoms
- 400 Bad Request when initiating calls
- "Call initiation failed" errors
- Calls not connecting

#### Phone Number Issues

**Invalid Phone Number Format**
```json
{
  "error": "validation_error",
  "message": "Phone number must be in valid international format"
}
```

**Common Phone Number Fixes:**
```bash
# ❌ Invalid formats
"1234567890"      # Missing country code
"(123) 456-7890"  # Not international format
"+1 (123) 456-7890" # Extra formatting

# ✅ Valid formats
"+1234567890"     # US number
"+441234567890"   # UK number
"+33123456789"    # French number
```

**Agent ID Mismatch**
```json
{
  "error": "agent_id_mismatch",
  "message": "Agent ID in URL path must match agent ID in request body"
}
```

**Solution:**
```bash
# Ensure agent_id in URL matches request body
curl -X POST "http://localhost:8000/api/v1/calls/agent_123" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "phone_number": "+1234567890",
    "template_context": {},
    "agent_id": "agent_123"
  }'
```

### 5. External Service Connectivity Issues

#### Symptoms
- Calls initiated but fail to connect
- "External service error" messages
- Timeouts during API calls

#### Ultravox API Issues

**Check Ultravox Connectivity**
```bash
# Test Ultravox API directly
curl -X GET "https://api.ultravox.ai/api/agents" \
  -H "Authorization: Bearer $ULTRAVOX_API_KEY"
```

**Common Ultravox Issues:**
- Invalid or expired API key
- Rate limiting from Ultravox
- Network connectivity issues
- Ultravox service outage

**Solutions:**
- Verify API key in Ultravox dashboard
- Check Ultravox status page
- Implement retry logic with exponential backoff
- Contact Ultravox support if persistent

#### Twilio API Issues

**Check Twilio Connectivity**
```bash
# Test Twilio API directly
curl -X GET "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID.json" \
  -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN"
```

**Common Twilio Issues:**
- Invalid credentials
- Insufficient account balance
- Phone number not verified (trial accounts)
- Geographic restrictions

**Solutions:**
- Verify credentials in Twilio Console
- Check account balance
- Verify phone numbers for trial accounts
- Review geographic permissions

### 6. Rate Limiting Issues

#### Symptoms
- 429 Too Many Requests responses
- "Rate limit exceeded" errors
- Intermittent request failures

#### Solutions

**Check Rate Limit Headers**
```bash
curl -I -X GET "http://localhost:8000/api/v1/agents" \
  -H "X-API-Key: $API_KEY"

# Look for these headers:
# X-RateLimit-Limit: 60
# X-RateLimit-Remaining: 45
# X-RateLimit-Reset: 1640995200
```

**Implement Retry Logic**
```python
import time
import requests

def make_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

**Adjust Rate Limits**
```bash
# Configure higher rate limits via environment variables
export RATE_LIMIT_PER_MINUTE=120
export RATE_LIMIT_PER_HOUR=2000
export RATE_LIMIT_BURST=20
```

### 7. Memory and Performance Issues

#### Symptoms
- Slow response times
- Memory usage growing over time
- Service becoming unresponsive

#### Monitoring and Diagnostics

**Check Service Metrics**
```bash
curl -X GET "http://localhost:8000/api/v1/metrics" \
  -H "X-API-Key: $API_KEY"
```

**Monitor Resource Usage**
```bash
# Check memory usage
free -h

# Check CPU usage
top -p $(pgrep -f "python.*main.py")

# Check disk space
df -h
```

#### Solutions

**Memory Leaks**
- Restart the service periodically
- Monitor for unclosed HTTP connections
- Check for circular references in code

**Performance Optimization**
```bash
# Increase worker processes
export WORKERS=4

# Adjust connection pool sizes
export HTTP_POOL_SIZE=20
export HTTP_MAX_CONNECTIONS=100
```

### 8. SSL/TLS Certificate Issues

#### Symptoms
- SSL certificate verification errors
- "Certificate verify failed" messages
- HTTPS connection failures

#### Solutions

**Development Environment**
```bash
# Disable SSL verification (development only)
export PYTHONHTTPSVERIFY=0
export SSL_VERIFY=false
```

**Production Environment**
```bash
# Update CA certificates
sudo apt-get update && sudo apt-get install ca-certificates

# Or on CentOS/RHEL
sudo yum update ca-certificates
```

### 9. Database/Storage Issues

#### Symptoms
- Agent data not persisting
- Inconsistent agent states
- Storage-related errors

#### Solutions

**Check Storage Configuration**
```bash
# Verify storage directory exists and is writable
ls -la /path/to/storage
touch /path/to/storage/test.txt
rm /path/to/storage/test.txt
```

**Clear Corrupted Data**
```bash
# Backup and clear storage (if using file-based storage)
cp -r /path/to/storage /path/to/storage.backup
rm -rf /path/to/storage/*
```

## Debugging Tools and Commands

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json
```

### Network Debugging

```bash
# Test connectivity to external services
curl -v https://api.ultravox.ai
curl -v https://api.twilio.com

# Check DNS resolution
nslookup api.ultravox.ai
nslookup api.twilio.com

# Test port connectivity
telnet api.ultravox.ai 443
telnet api.twilio.com 443
```

### Service Debugging

```bash
# Check service status
systemctl status ultravox-twilio-service

# View recent logs
journalctl -u ultravox-twilio-service -f

# Check process information
ps aux | grep python
netstat -tlnp | grep :8000
```

## Error Code Reference

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Invalid request data, validation errors |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Agent not found, invalid endpoint |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Service error, external API failure |
| 503 | Service Unavailable | Service starting up, configuration error |

### Application Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `validation_error` | Request data validation failed | Check request format and data types |
| `agent_not_found` | Specified agent doesn't exist | Verify agent ID, create agent if needed |
| `agent_creation_failed` | Agent creation failed | Check Ultravox API connectivity and credentials |
| `call_initiation_failed` | Call could not be initiated | Verify phone number format and Twilio credentials |
| `configuration_error` | Service configuration invalid | Check environment variables |
| `external_service_error` | External API call failed | Check Ultravox/Twilio service status |
| `rate_limit_exceeded` | Too many requests | Implement retry logic, reduce request rate |

## Getting Help

### Log Collection

When reporting issues, collect these logs:

```bash
# Application logs
tail -n 1000 /path/to/app.log > issue_logs.txt

# System logs
journalctl -u ultravox-twilio-service --since "1 hour ago" > system_logs.txt

# Configuration (remove sensitive data)
env | grep -E "(ULTRAVOX|TWILIO|API)" | sed 's/=.*/=***/' > config.txt
```

### Health Check Report

```bash
# Generate comprehensive health report
curl -s "http://localhost:8000/api/v1/health/detailed" | jq . > health_report.json
curl -s "http://localhost:8000/api/v1/metrics" | jq . > metrics_report.json
```

### Contact Information

- **GitHub Issues**: [Repository Issues Page]
- **Documentation**: [API Documentation](./api.md)
- **Examples**: [Usage Examples](./examples.md)

### Before Reporting Issues

1. Check this troubleshooting guide
2. Verify your configuration
3. Test with the health check endpoints
4. Collect relevant logs
5. Try reproducing with minimal examples
6. Check for known issues in the repository

## Prevention Best Practices

### Configuration Management
- Use environment variables for all configuration
- Validate configuration on startup
- Document all required settings
- Use configuration templates

### Monitoring
- Implement health checks in your deployment
- Monitor external service connectivity
- Set up alerting for error rates
- Track performance metrics

### Error Handling
- Implement proper retry logic
- Use circuit breakers for external services
- Log errors with sufficient context
- Provide meaningful error messages to users

### Testing
- Test with invalid inputs
- Verify external service integration
- Load test your deployment
- Test failure scenarios

This troubleshooting guide should help you quickly identify and resolve most common issues with the Ultravox-Twilio Integration Service.
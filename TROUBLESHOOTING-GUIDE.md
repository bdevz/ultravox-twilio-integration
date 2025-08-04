# 🔧 Troubleshooting Guide: "API request failed" Error

## 🎯 Quick Diagnosis

The "API request failed" error typically occurs when the server can't communicate with external APIs (Ultravox, ElevenLabs, or Twilio). Here's how to systematically identify and fix the issue:

## 🚀 Step 1: Run the API Troubleshooter

```bash
python troubleshoot-apis.py
```

This script will:
- ✅ Check all environment variables
- ✅ Test service initialization
- ✅ Test connectivity to Ultravox API
- ✅ Test connectivity to ElevenLabs API  
- ✅ Test connectivity to Twilio API

## 🧪 Step 2: Test with Minimal Server

If the troubleshooter shows issues, test the frontend with mock data:

```bash
python minimal-server.py
```

This will:
- ✅ Start a server with mock responses
- ✅ Test if the web interface works
- ✅ Isolate frontend vs backend issues

## 🔍 Step 3: Common Issues & Solutions

### Issue 1: Environment Variables Missing
**Symptoms:** "Missing required environment variables" error

**Solution:** Check your `.env` file contains:
```bash
# Required variables
ULTRAVOX_API_KEY=your_key_here
ULTRAVOX_BASE_URL=https://api.ultravox.ai
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_PHONE_NUMBER=+1234567890
ELEVENLABS_API_KEY=your_key_here
ENABLE_ELEVENLABS=true
```

### Issue 2: Invalid API Keys
**Symptoms:** "Authentication failed" in troubleshooter

**Solutions:**
- **Ultravox:** Verify your API key at https://dashboard.ultravox.ai
- **ElevenLabs:** Verify your API key at https://elevenlabs.io/app/speech-synthesis
- **Twilio:** Verify credentials at https://console.twilio.com

### Issue 3: Network/Firewall Issues
**Symptoms:** "Connection error" in troubleshooter

**Solutions:**
- Check internet connectivity
- Verify firewall allows outbound HTTPS (port 443)
- Try from a different network

### Issue 4: API Rate Limits
**Symptoms:** HTTP 429 errors in logs

**Solutions:**
- Wait a few minutes and retry
- Check your API usage quotas
- Upgrade your API plan if needed

### Issue 5: Service Initialization Errors
**Symptoms:** Services fail to initialize

**Solutions:**
- Check Python dependencies: `pip install -r requirements.txt`
- Verify all imports work: `python debug-services.py`
- Check for missing files in `app/` directory

## 🔧 Step 4: Debug Service by Service

### Debug Ultravox Service
```bash
# Test Ultravox API directly
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.ultravox.ai/api/agents
```

### Debug ElevenLabs Service
```bash
# Test ElevenLabs API directly
curl -H "xi-api-key: YOUR_API_KEY" \
     https://api.elevenlabs.io/v1/voices
```

### Debug Twilio Service
```bash
# Test Twilio API directly
curl -u "ACCOUNT_SID:AUTH_TOKEN" \
     https://api.twilio.com/2010-04-01/Accounts/ACCOUNT_SID.json
```

## 🎯 Step 5: Progressive Testing

1. **Start with minimal server** (mock data)
2. **Add one service at a time** to identify which fails
3. **Check logs** for specific error messages
4. **Test individual API endpoints** before full integration

## 📊 Common Error Patterns

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| "API request failed" | Generic API error | Run troubleshooter |
| "Authentication failed" | Invalid API key | Check credentials |
| "Service not available" | Service not initialized | Check environment vars |
| "Connection error" | Network issue | Check connectivity |
| "Quota exceeded" | API limits reached | Wait or upgrade plan |

## 🚨 Emergency Workaround

If you need to demo the interface immediately:

1. **Use minimal server:** `python minimal-server.py`
2. **Shows full UI** with mock data
3. **Demonstrates functionality** without real API calls
4. **Allows frontend testing** while fixing backend

## 📝 Logging & Debugging

### Enable Debug Logging
Add to your `.env`:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

### Check Server Logs
Look for specific error messages in the server output:
- Authentication errors
- Network timeouts
- Invalid responses
- Service initialization failures

### Test Individual Components
```bash
# Test config loading
python debug-services.py

# Test API connectivity  
python troubleshoot-apis.py

# Test with mock data
python minimal-server.py
```

## ✅ Success Checklist

Before running the full server, ensure:
- [ ] All environment variables are set
- [ ] API keys are valid and active
- [ ] Network connectivity works
- [ ] Services initialize without errors
- [ ] Individual API calls succeed

## 🎉 Next Steps

Once troubleshooting is complete:
1. **Run full server:** `python run-server.py`
2. **Test all endpoints:** `python test-api.py`
3. **Use web interface:** Open http://localhost:8001
4. **Create agents and make calls**

The systematic approach above should identify and resolve the "API request failed" error quickly!
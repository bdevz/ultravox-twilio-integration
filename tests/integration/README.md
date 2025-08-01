# Integration Tests

This directory contains integration tests that interact with real external services (Ultravox and Twilio APIs). These tests require actual API credentials and may incur charges.

## Prerequisites

### Required Environment Variables

Before running integration tests, you must set the following environment variables:

#### Ultravox API Credentials
```bash
export TEST_ULTRAVOX_API_KEY="your_ultravox_api_key_here"
export TEST_ULTRAVOX_BASE_URL="https://api.ultravox.ai"  # Optional, defaults to production URL
```

#### Twilio API Credentials
```bash
export TEST_TWILIO_ACCOUNT_SID="your_twilio_account_sid_here"
export TEST_TWILIO_AUTH_TOKEN="your_twilio_auth_token_here"
export TEST_TWILIO_PHONE_NUMBER="your_twilio_phone_number_here"  # Format: +1234567890
```

#### Test Configuration
```bash
export TEST_PHONE_NUMBER="+15551234567"  # Safe test number that won't actually be called
```

### Setting Up Test Credentials

#### Ultravox Test Credentials
1. Sign up for an Ultravox account at https://ultravox.ai
2. Navigate to your API settings
3. Generate a test API key
4. Set the `TEST_ULTRAVOX_API_KEY` environment variable

#### Twilio Test Credentials
1. Sign up for a Twilio account at https://twilio.com
2. Navigate to Console Dashboard
3. Find your Account SID and Auth Token
4. Purchase a phone number or use your trial number
5. Set the Twilio environment variables

**Important**: Use Twilio test credentials when possible to avoid charges.

## Running Integration Tests

### Run All Integration Tests
```bash
pytest tests/integration/ -v
```

### Run Specific Test Categories

#### Ultravox API Tests Only
```bash
pytest tests/integration/test_ultravox_integration.py -v -m ultravox
```

#### Twilio API Tests Only
```bash
pytest tests/integration/test_twilio_integration.py -v -m twilio
```

#### End-to-End Tests Only
```bash
pytest tests/integration/test_e2e_call_flow.py -v -m e2e
```

### Skip Slow Tests
```bash
pytest tests/integration/ -v -m "not slow"
```

### Run with Specific Markers
```bash
# Run only tests that require both Ultravox and Twilio
pytest tests/integration/ -v -m "ultravox and twilio"

# Run only end-to-end tests
pytest tests/integration/ -v -m e2e
```

## Test Structure

### Test Files

- `test_ultravox_integration.py` - Tests for Ultravox API interactions
  - Agent CRUD operations
  - Join URL generation
  - Error handling
  
- `test_twilio_integration.py` - Tests for Twilio API interactions
  - Call creation
  - TwiML generation
  - Error handling
  
- `test_e2e_call_flow.py` - End-to-end tests
  - Complete call flow (agent creation → join URL → Twilio call)
  - Multiple calls with same agent
  - Complex template contexts
  - Error recovery scenarios
  - Performance tests

### Test Markers

- `@pytest.mark.ultravox` - Requires Ultravox API credentials
- `@pytest.mark.twilio` - Requires Twilio API credentials
- `@pytest.mark.e2e` - End-to-end integration test
- `@pytest.mark.slow` - Slow-running test (may take several seconds)

## Safety Considerations

### Avoiding Charges

1. **Use Test Credentials**: Always use test/sandbox credentials when available
2. **Safe Phone Numbers**: Use phone numbers that won't actually connect (like +15551234567)
3. **Cleanup**: Tests include cleanup fixtures to remove created agents
4. **Limited Scope**: Tests create minimal resources and clean up after themselves

### Test Data

- All test agents are prefixed with "Integration Test" or "E2E Test"
- Template contexts include test identifiers
- Phone numbers use safe test formats

## Troubleshooting

### Common Issues

#### Missing Credentials
```
SKIPPED [1] tests/integration/conftest.py:45: Missing required credentials: ultravox_api_key
```
**Solution**: Set the required environment variables

#### Invalid Credentials
```
UltravoxAPIError: Failed to create agent: Unauthorized
```
**Solution**: Verify your API credentials are correct and active

#### Network Issues
```
ConnectionError: Failed to establish connection
```
**Solution**: Check your internet connection and API endpoint URLs

#### Rate Limiting
```
TwilioCallError: Too Many Requests
```
**Solution**: Wait a moment and retry, or use test credentials with higher limits

### Debug Mode

Run tests with verbose output and no capture to see detailed logs:
```bash
pytest tests/integration/ -v -s --tb=long
```

### Test Configuration Validation

You can validate your test configuration by running:
```bash
python -c "
import os
required = ['TEST_ULTRAVOX_API_KEY', 'TEST_TWILIO_ACCOUNT_SID', 'TEST_TWILIO_AUTH_TOKEN', 'TEST_TWILIO_PHONE_NUMBER']
missing = [var for var in required if not os.getenv(var)]
if missing:
    print(f'Missing: {missing}')
else:
    print('All required environment variables are set')
"
```

## Contributing

When adding new integration tests:

1. Use appropriate markers (`@pytest.mark.ultravox`, `@pytest.mark.twilio`, etc.)
2. Include cleanup fixtures for any created resources
3. Use safe test data that won't incur unnecessary charges
4. Add appropriate error handling tests
5. Document any new environment variables needed
6. Consider performance impact and mark slow tests appropriately

## CI/CD Considerations

Integration tests should typically be run in a separate CI pipeline or stage because:

1. They require external API credentials
2. They may incur costs
3. They depend on external service availability
4. They are slower than unit tests

Consider running integration tests:
- On a schedule (nightly/weekly)
- Before major releases
- In a dedicated testing environment
- With appropriate credential management
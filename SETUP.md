# 🚀 Ultravox-Twilio Integration Service Setup

This guide will help you set up the Ultravox-Twilio Integration Service for your team.

## 📋 Prerequisites

- Python 3.8+
- Ultravox API account and API key
- Twilio account with phone number
- Git

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ultravox-twilio-integration
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your actual credentials:
```bash
# Ultravox API Configuration
ULTRAVOX_API_KEY=your_actual_ultravox_api_key
ULTRAVOX_BASE_URL=https://api.ultravox.ai

# Twilio API Configuration
TWILIO_ACCOUNT_SID=your_actual_twilio_account_sid
TWILIO_AUTH_TOKEN=your_actual_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number
TWILIO_USER_SID=your_actual_twilio_user_sid

# Application Configuration
DEBUG=false
LOG_LEVEL=INFO
PORT=8000

# Security
API_KEY=your_secure_api_key_for_web_interface
```

## 🔑 Getting Your API Keys

### Ultravox API Key
1. Go to [Ultravox Dashboard](https://dashboard.ultravox.ai)
2. Navigate to API Keys section
3. Create a new API key
4. Copy the key to your `.env` file

### Twilio Credentials
1. Go to [Twilio Console](https://console.twilio.com)
2. Find your Account SID and Auth Token
3. Purchase a phone number if you don't have one
4. Copy all credentials to your `.env` file

## 🧪 Testing Your Setup

### 1. Validate Configuration
```bash
python scripts/validate-config.py
```

### 2. Check Development Environment
```bash
python scripts/check-dev-env.py
```

### 3. Run Tests
```bash
pytest tests/
```

## 🚀 Running the Service

### Option 1: Full Service (Production-like)
```bash
python app/main.py
```
Access at: http://localhost:8000

### Option 2: Simple Web Interface (Development)
```bash
python simple-web-server.py
```
Access at: http://localhost:8001

## 🌐 Using the Web Interface

1. Open your browser to the service URL
2. **Create an AI Agent**:
   - Enter agent name (letters, numbers, hyphens, underscores only)
   - Write agent instructions/prompt
   - Click "Create Agent"

3. **Make a Voice Call**:
   - Select an agent from the list
   - Enter phone number in international format (+1234567890)
   - Click "Make Call"

## 📱 Phone Number Format

Always use international format:
- ✅ `+12123456789` (US number)
- ✅ `+447123456789` (UK number)
- ❌ `(212) 345-6789` (Invalid)
- ❌ `212-345-6789` (Invalid)

## 🔒 Security Notes

- Never commit `.env` files to Git
- Keep API keys secure and rotate them regularly
- Use strong API keys for the web interface
- Consider using environment-specific configurations

## 🐛 Troubleshooting

### Common Issues

1. **"API request failed"** when creating agents:
   - Check agent name format (no spaces or special characters)
   - Verify Ultravox API key is correct

2. **Call fails to connect**:
   - Verify Twilio credentials
   - Check phone number format
   - Ensure Twilio account has sufficient balance

3. **Web interface not loading**:
   - Check if port is already in use
   - Verify all environment variables are set

### Getting Help

1. Check the logs for detailed error messages
2. Validate your configuration with `scripts/validate-config.py`
3. Review the troubleshooting guide in `docs/troubleshooting.md`

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Development Guide](docs/development.md)
- [Deployment Guide](docs/deployment.md)
- [Security Guide](docs/security.md)

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

[Add your license information here]
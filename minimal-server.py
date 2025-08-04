#!/usr/bin/env python3
"""
Minimal server for testing - bypasses complex service initialization.
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="Minimal Test Server")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_web_interface():
    """Serve the web interface."""
    return FileResponse("static/index.html")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Minimal server running",
        "environment": {
            "ultravox_key_set": bool(os.getenv("ULTRAVOX_API_KEY")),
            "elevenlabs_key_set": bool(os.getenv("ELEVENLABS_API_KEY")),
            "twilio_sid_set": bool(os.getenv("TWILIO_ACCOUNT_SID")),
            "enable_elevenlabs": os.getenv("ENABLE_ELEVENLABS", "false").lower() == "true"
        }
    }

@app.get("/api/v1/voices")
async def list_voices():
    """Mock voices endpoint for testing."""
    # Return mock data to test the frontend
    return [
        {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "name": "Rachel",
            "category": "premade",
            "description": "Mock voice for testing"
        },
        {
            "voice_id": "AZnzlk1XvdvUeBnXmlld",
            "name": "Domi",
            "category": "premade", 
            "description": "Mock voice for testing"
        }
    ]

@app.get("/api/v1/voices/{voice_id}/preview")
async def preview_voice(voice_id: str):
    """Mock voice preview endpoint."""
    # Return a simple response for testing
    from fastapi.responses import Response
    return Response(
        content=b"mock audio data",
        media_type="audio/mpeg"
    )

@app.post("/api/v1/agents")
async def create_ultravox_agent(agent_data: dict):
    """Mock Ultravox agent creation."""
    return {
        "id": f"mock_ultravox_{hash(agent_data.get('name', 'test')) % 10000}",
        "config": {
            "name": agent_data.get("name", "Test Agent"),
            "prompt": agent_data.get("prompt", "Test prompt")
        },
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    }

@app.post("/api/v1/agents/elevenlabs")
async def create_elevenlabs_agent(agent_data: dict):
    """Mock ElevenLabs agent creation."""
    return {
        "id": f"mock_elevenlabs_{hash(agent_data.get('name', 'test')) % 10000}",
        "name": agent_data.get("name", "Test Agent"),
        "agent_type": "elevenlabs",
        "voice_id": agent_data.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z"
    }

@app.get("/api/v1/agents/elevenlabs")
async def list_elevenlabs_agents():
    """Mock ElevenLabs agent listing."""
    return [
        {
            "id": "mock_elevenlabs_1",
            "name": "Mock ElevenLabs Agent",
            "agent_type": "elevenlabs",
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z"
        }
    ]

@app.get("/api/v1/agents")
async def list_all_agents():
    """Mock unified agent listing."""
    return {
        "agents": [
            {
                "id": "mock_ultravox_1",
                "name": "Mock Ultravox Agent",
                "agent_type": "ultravox",
                "status": "active",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            },
            {
                "id": "mock_elevenlabs_1",
                "name": "Mock ElevenLabs Agent",
                "agent_type": "elevenlabs",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "status": "active",
                "created_at": "2025-01-01T00:00:00Z"
            }
        ],
        "total_count": 2
    }

@app.post("/api/v1/calls/{agent_id}")
async def create_ultravox_call(agent_id: str, call_data: dict):
    """Mock Ultravox call creation."""
    return {
        "call_sid": f"CA{'a' * 32}",
        "status": "initiated",
        "created_at": "2025-01-01T00:00:00Z"
    }

@app.post("/api/v1/calls/elevenlabs/{agent_id}")
async def create_elevenlabs_call(agent_id: str, call_data: dict):
    """Mock ElevenLabs call creation."""
    return {
        "call_sid": f"CA{'b' * 32}",
        "status": "initiated",
        "created_at": "2025-01-01T00:00:00Z"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    print(f"🚀 Starting MINIMAL test server on port {port}")
    print(f"📱 Web Interface: http://localhost:{port}")
    print(f"🔍 Health Check: http://localhost:{port}/api/v1/health")
    print("⚠️  This server uses MOCK data - no real API calls!")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
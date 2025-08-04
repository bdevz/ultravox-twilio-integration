#!/usr/bin/env python3
"""
Simple demo server for ElevenLabs Conversational AI integration.
Uses mock data instead of real APIs for demonstration.
"""

import os
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create FastAPI app
app = FastAPI(title="Ultravox-ElevenLabs Demo Interface")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data storage
mock_ultravox_agents = []
mock_elevenlabs_agents = []
mock_voices = [
    {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "name": "Rachel",
        "category": "premade",
        "description": "Young American female voice",
        "preview_url": "https://example.com/preview1.mp3",
        "labels": {"accent": "american", "age": "young", "gender": "female"}
    },
    {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Bella",
        "category": "premade", 
        "description": "Young American female voice",
        "preview_url": "https://example.com/preview2.mp3",
        "labels": {"accent": "american", "age": "young", "gender": "female"}
    },
    {
        "voice_id": "ErXwobaYiN019PkySvjV",
        "name": "Antoni",
        "category": "premade",
        "description": "Young American male voice",
        "preview_url": "https://example.com/preview3.mp3", 
        "labels": {"accent": "american", "age": "young", "gender": "male"}
    }
]

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_web_interface():
    """Serve the web interface."""
    return FileResponse("static/index.html")

@app.get("/api/v1/health")
async def health_check():
    """Simple health check."""
    return {
        "status": "healthy",
        "service": "ultravox-elevenlabs-demo",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ultravox": "mock",
            "elevenlabs": "mock", 
            "twilio": "mock"
        }
    }

@app.get("/api/v1/health/detailed")
async def detailed_health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "ultravox-elevenlabs-demo",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ultravox": {"status": "healthy", "type": "mock"},
            "elevenlabs": {"status": "healthy", "type": "mock"},
            "twilio": {"status": "healthy", "type": "mock"}
        },
        "version": "1.0.0-demo"
    }

# ============================================================================
# Ultravox Mock Endpoints
# ============================================================================

@app.post("/api/v1/agents")
async def create_ultravox_agent(agent_data: dict):
    """Create a mock Ultravox agent."""
    print(f"🤖 Creating mock Ultravox agent: {agent_data}")
    
    agent = {
        "id": f"ultravox_{uuid.uuid4().hex[:8]}",
        "config": {
            "name": agent_data["name"],
            "prompt": agent_data["prompt"],
            "voice": agent_data.get("voice", "default"),
            "language": agent_data.get("language", "en"),
            "template_variables": agent_data.get("template_variables", {})
        },
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    mock_ultravox_agents.append(agent)
    print(f"✅ Created mock Ultravox agent: {agent['id']}")
    
    return agent

@app.post("/api/v1/calls/{agent_id}")
async def create_ultravox_call(agent_id: str, call_data: dict):
    """Create a mock Ultravox call."""
    print(f"📞 Creating mock Ultravox call with agent: {agent_id}")
    
    # Find agent
    agent = next((a for a in mock_ultravox_agents if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    call_result = {
        "call_sid": f"CA{uuid.uuid4().hex[:32]}",
        "status": "initiated",
        "agent_id": agent_id,
        "phone_number": call_data["phone_number"],
        "call_type": "ultravox",
        "created_at": datetime.now().isoformat()
    }
    
    print(f"✅ Created mock Ultravox call: {call_result['call_sid']}")
    return call_result

# ============================================================================
# ElevenLabs Mock Endpoints  
# ============================================================================

@app.get("/api/v1/voices")
async def list_voices():
    """List mock ElevenLabs voices."""
    print("📋 Listing mock ElevenLabs voices...")
    print(f"✅ Returning {len(mock_voices)} mock voices")
    return mock_voices

@app.get("/api/v1/voices/{voice_id}/preview")
async def preview_voice(voice_id: str):
    """Generate a mock voice preview."""
    print(f"🔊 Generating mock voice preview for {voice_id}...")
    
    # Find voice
    voice = next((v for v in mock_voices if v["voice_id"] == voice_id), None)
    if not voice:
        raise HTTPException(status_code=404, detail=f"Voice {voice_id} not found")
    
    # Return a small mock audio file (empty MP3 header)
    mock_audio = b'\xff\xfb\x90\x00' + b'\x00' * 100  # Minimal MP3 header + silence
    
    from fastapi.responses import Response
    return Response(
        content=mock_audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename=preview_{voice_id}.mp3",
            "Content-Length": str(len(mock_audio))
        }
    )

@app.post("/api/v1/agents/elevenlabs")
async def create_elevenlabs_agent(agent_data: dict):
    """Create a mock ElevenLabs agent."""
    print(f"🗣️ Creating mock ElevenLabs agent: {agent_data}")
    
    # Validate voice exists
    voice = next((v for v in mock_voices if v["voice_id"] == agent_data["voice_id"]), None)
    if not voice:
        raise HTTPException(status_code=404, detail=f"Voice {agent_data['voice_id']} not found")
    
    agent = {
        "id": f"elevenlabs_{uuid.uuid4().hex[:8]}",
        "name": agent_data["name"],
        "agent_type": "elevenlabs",
        "voice_id": agent_data["voice_id"],
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": None,
        "config": {
            "name": agent_data["name"],
            "system_prompt": agent_data["system_prompt"],
            "voice_id": agent_data["voice_id"],
            "template_variables": agent_data.get("template_variables", {})
        }
    }
    
    mock_elevenlabs_agents.append(agent)
    print(f"✅ Created mock ElevenLabs agent: {agent['id']}")
    
    return agent

@app.get("/api/v1/agents/elevenlabs")
async def list_elevenlabs_agents():
    """List mock ElevenLabs agents."""
    print("📋 Listing mock ElevenLabs agents...")
    print(f"✅ Returning {len(mock_elevenlabs_agents)} mock ElevenLabs agents")
    return mock_elevenlabs_agents

@app.post("/api/v1/calls/elevenlabs/{agent_id}")
async def create_elevenlabs_call(agent_id: str, call_data: dict):
    """Create a mock ElevenLabs conversational call."""
    print(f"📞 Creating mock ElevenLabs call with agent: {agent_id}")
    
    # Find agent
    agent = next((a for a in mock_elevenlabs_agents if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    call_result = {
        "call_sid": f"CA{uuid.uuid4().hex[:32]}",
        "status": "initiated", 
        "agent_id": agent_id,
        "phone_number": call_data["phone_number"],
        "call_type": "elevenlabs_conversational",
        "created_at": datetime.now().isoformat()
    }
    
    print(f"✅ Created mock ElevenLabs call: {call_result['call_sid']}")
    return call_result

# ============================================================================
# Unified Endpoints
# ============================================================================

@app.get("/api/v1/agents")
async def list_all_agents():
    """List all agents from both platforms."""
    print("📋 Listing all mock agents from both platforms...")
    
    all_agents = []
    
    # Add Ultravox agents
    for agent in mock_ultravox_agents:
        all_agents.append({
            "id": agent["id"],
            "name": agent["config"]["name"],
            "agent_type": "ultravox",
            "status": agent["status"],
            "created_at": agent["created_at"],
            "updated_at": agent["updated_at"]
        })
    
    # Add ElevenLabs agents
    for agent in mock_elevenlabs_agents:
        all_agents.append({
            "id": agent["id"],
            "name": agent["name"],
            "agent_type": "elevenlabs",
            "voice_id": agent["voice_id"],
            "status": agent["status"],
            "created_at": agent["created_at"],
            "updated_at": agent["updated_at"]
        })
    
    result = {
        "agents": all_agents,
        "total_count": len(all_agents),
        "ultravox_count": len(mock_ultravox_agents),
        "elevenlabs_count": len(mock_elevenlabs_agents)
    }
    
    print(f"✅ Returning {len(all_agents)} total mock agents")
    return result

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8004))
    print("🎭 Starting Mock Demo Server...")
    print(f"📱 Web Interface: http://localhost:{port}")
    print(f"🔍 Health Check: http://localhost:{port}/api/v1/health")
    print("=" * 50)
    print("🎯 This is a DEMO server using mock data")
    print("🎯 No real API calls are made to Ultravox, ElevenLabs, or Twilio")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=port)
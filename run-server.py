#!/usr/bin/env python3
"""
Simple script to run the ElevenLabs Conversational AI server.
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

# Debug: Check if environment variables are loaded
print(f"🔍 Environment check:")
print(f"   ENABLE_ELEVENLABS: {os.getenv('ENABLE_ELEVENLABS')}")
print(f"   ELEVENLABS_API_KEY: {'✅ Set' if os.getenv('ELEVENLABS_API_KEY') else '❌ Not set'}")
print(f"   ULTRAVOX_API_KEY: {'✅ Set' if os.getenv('ULTRAVOX_API_KEY') else '❌ Not set'}")

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.config_service import ConfigService
from app.services.http_client_service import HTTPClientService
from app.services.agent_service import AgentService
from app.services.call_service import CallService
from app.services.voice_service import VoiceService
from app.services.elevenlabs_agent_service import ElevenLabsAgentService
from app.services.elevenlabs_conversation_service import ElevenLabsConversationService
from app.models.agent import AgentConfig
from app.models.call import CallRequest
from app.models.elevenlabs import (
    ElevenLabsAgentConfig, 
    ElevenLabsConversationalCallRequest
)

# Create FastAPI app
app = FastAPI(title="ElevenLabs Conversational AI Integration")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
print("🔧 Initializing services...")
config_service = ConfigService()
http_client = HTTPClientService()

# Initialize Ultravox services
try:
    agent_service = AgentService(http_client, config_service)
    call_service = CallService(config_service, http_client)
    print("✅ Ultravox services initialized")
except Exception as e:
    print(f"⚠️  Ultravox services failed: {e}")
    agent_service = None
    call_service = None

# Initialize ElevenLabs services
elevenlabs_agent_service = None
elevenlabs_conversation_service = None
voice_service = None

try:
    print(f"🔍 Checking ElevenLabs enabled: {config_service.is_elevenlabs_enabled()}")
    if config_service.is_elevenlabs_enabled():
        print("🔧 Getting ElevenLabs config...")
        elevenlabs_config = config_service.get_elevenlabs_config()
        print("🔧 Creating VoiceService...")
        voice_service = VoiceService(elevenlabs_config)
        print("🔧 Creating ElevenLabsAgentService...")
        elevenlabs_agent_service = ElevenLabsAgentService(elevenlabs_config, voice_service)
        print("🔧 Creating ElevenLabsConversationService...")
        elevenlabs_conversation_service = ElevenLabsConversationService(elevenlabs_config)
        
        # Update call service with ElevenLabs support
        if call_service:
            call_service.elevenlabs_conversation_service = elevenlabs_conversation_service
        
        print("✅ ElevenLabs services initialized")
        print(f"   Voice service: {voice_service is not None}")
        print(f"   Agent service: {elevenlabs_agent_service is not None}")
    else:
        print("⚠️  ElevenLabs services disabled")
except Exception as e:
    print(f"⚠️  ElevenLabs services failed: {e}")
    import traceback
    traceback.print_exc()

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
        "services": {
            "ultravox": agent_service is not None,
            "elevenlabs": elevenlabs_agent_service is not None,
            "voice": voice_service is not None
        }
    }

# Ultravox endpoints
@app.post("/api/v1/agents")
async def create_ultravox_agent(agent_data: dict):
    """Create an Ultravox agent."""
    if not agent_service:
        raise HTTPException(status_code=503, detail="Ultravox service not available")
    
    try:
        agent_config = AgentConfig(
            name=agent_data["name"],
            prompt=agent_data["prompt"],
            voice=agent_data.get("voice", "default"),
            language=agent_data.get("language", "en")
        )
        
        agent = await agent_service.create_agent(agent_config)
        
        return {
            "id": agent.id,
            "config": {
                "name": agent.config.name,
                "prompt": agent.config.prompt
            },
            "status": agent.status,
            "created_at": agent.created_at.isoformat(),
            "updated_at": agent.updated_at.isoformat()
        }
    except Exception as e:
        print(f"❌ Ultravox agent creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/calls/{agent_id}")
async def create_ultravox_call(agent_id: str, call_data: dict):
    """Create an Ultravox call."""
    if not call_service:
        raise HTTPException(status_code=503, detail="Call service not available")
    
    try:
        call_request = CallRequest(
            phone_number=call_data["phone_number"],
            agent_id=agent_id,
            template_context=call_data.get("template_context", {})
        )
        
        call_result = await call_service.initiate_call(call_request)
        
        return {
            "call_sid": call_result.call_sid,
            "status": call_result.status,
            "created_at": call_result.created_at.isoformat()
        }
    except Exception as e:
        print(f"❌ Ultravox call error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ElevenLabs endpoints
@app.get("/api/v1/voices")
async def list_voices():
    """List ElevenLabs voices."""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not available")
    
    try:
        voices = await voice_service.list_voices()
        return [{
            "voice_id": voice.voice_id,
            "name": voice.name,
            "category": voice.category,
            "description": voice.description
        } for voice in voices]
    except Exception as e:
        print(f"❌ Voice listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/voices/{voice_id}/preview")
async def preview_voice(voice_id: str):
    """Preview a voice."""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not available")
    
    try:
        audio_data = await voice_service.preview_voice(voice_id)
        
        from fastapi.responses import Response
        return Response(
            content=audio_data.content,
            media_type=audio_data.content_type
        )
    except Exception as e:
        print(f"❌ Voice preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/agents/elevenlabs")
async def create_elevenlabs_agent(agent_data: dict):
    """Create an ElevenLabs agent."""
    if not elevenlabs_agent_service:
        raise HTTPException(status_code=503, detail="ElevenLabs agent service not available")
    
    try:
        agent_config = ElevenLabsAgentConfig(
            name=agent_data["name"],
            system_prompt=agent_data["system_prompt"],
            voice_id=agent_data["voice_id"],
            template_variables=agent_data.get("template_variables", {})
        )
        
        agent = await elevenlabs_agent_service.create_agent(agent_config)
        
        return {
            "id": agent.id,
            "name": agent.config.name,
            "agent_type": "elevenlabs",
            "voice_id": agent.config.voice_id,
            "status": agent.status,
            "created_at": agent.created_at.isoformat()
        }
    except Exception as e:
        print(f"❌ ElevenLabs agent creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents/elevenlabs")
async def list_elevenlabs_agents():
    """List ElevenLabs agents."""
    if not elevenlabs_agent_service:
        raise HTTPException(status_code=503, detail="ElevenLabs agent service not available")
    
    try:
        agents = await elevenlabs_agent_service.list_agents()
        return [{
            "id": agent.id,
            "name": agent.config.name,
            "agent_type": "elevenlabs",
            "voice_id": agent.config.voice_id,
            "status": agent.status,
            "created_at": agent.created_at.isoformat()
        } for agent in agents]
    except Exception as e:
        print(f"❌ ElevenLabs agent listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/calls/elevenlabs/{agent_id}")
async def create_elevenlabs_call(agent_id: str, call_data: dict):
    """Create an ElevenLabs conversational call."""
    if not call_service or not elevenlabs_conversation_service:
        raise HTTPException(status_code=503, detail="ElevenLabs call service not available")
    
    try:
        elevenlabs_request = ElevenLabsConversationalCallRequest(
            phone_number=call_data["phone_number"],
            agent_id=agent_id,
            template_context=call_data.get("template_context", {})
        )
        
        call_result = await call_service._initiate_elevenlabs_conversational_call(elevenlabs_request)
        
        return {
            "call_sid": call_result.call_sid,
            "status": call_result.status,
            "created_at": call_result.created_at.isoformat()
        }
    except Exception as e:
        print(f"❌ ElevenLabs call error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents")
async def list_all_agents():
    """List all agents from both platforms."""
    all_agents = []
    
    # Get Ultravox agents
    try:
        if agent_service:
            ultravox_agents = await agent_service.list_agents()
            for agent in ultravox_agents:
                all_agents.append({
                    "id": agent.id,
                    "name": agent.config.name,
                    "agent_type": "ultravox",
                    "status": agent.status,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": agent.updated_at.isoformat()
                })
    except Exception as e:
        print(f"⚠️ Failed to load Ultravox agents: {e}")
    
    # Get ElevenLabs agents
    try:
        if elevenlabs_agent_service:
            elevenlabs_agents = await elevenlabs_agent_service.list_agents()
            for agent in elevenlabs_agents:
                all_agents.append({
                    "id": agent.id,
                    "name": agent.config.name,
                    "agent_type": "elevenlabs",
                    "voice_id": agent.config.voice_id,
                    "status": agent.status,
                    "created_at": agent.created_at.isoformat()
                })
    except Exception as e:
        print(f"⚠️ Failed to load ElevenLabs agents: {e}")
    
    return {
        "agents": all_agents,
        "total_count": len(all_agents)
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    print(f"🚀 Starting server on port {port}")
    print(f"📱 Web Interface: http://localhost:{port}")
    print(f"🔍 Health Check: http://localhost:{port}/api/v1/health")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
#!/usr/bin/env python3
"""
Secure web server for the Ultravox-Twilio Integration Service.
This version reads credentials from environment variables instead of hardcoding them.
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

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.config_service import ConfigService
from app.services.http_client_service import HTTPClientService
from app.services.agent_service import AgentService
from app.services.call_service import CallService
from app.services.voice_service import VoiceService
from app.models.agent import AgentConfig
from app.models.call import CallRequest
from app.models.elevenlabs import ElevenLabsCallRequest, UnifiedCallRequest

def validate_environment():
    """Validate that all required environment variables are set."""
    required_vars = [
        "ULTRAVOX_API_KEY",
        "ULTRAVOX_BASE_URL", 
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please check your .env file or environment configuration.")
        print("📖 See SETUP.md for detailed configuration instructions.")
        sys.exit(1)
    
    print("✅ All required environment variables are set")

# Validate environment before starting
validate_environment()

# Create FastAPI app
app = FastAPI(title="Ultravox-Twilio Web Interface")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
config_service = ConfigService()
http_client = HTTPClientService()
agent_service = None
call_service = None
voice_service = None
elevenlabs_agent_service = None
elevenlabs_conversation_service = None

# Initialize call service
call_service = CallService(config_service, http_client)

# Initialize agent service
try:
    from app.services.agent_service import AgentService
    agent_service = AgentService(http_client, config_service)
    print("✅ Ultravox agent service initialized")
except Exception as e:
    print(f"⚠️  Ultravox agent service initialization failed: {e}")
    agent_service = None

# Check if ElevenLabs is available
elevenlabs_enabled = config_service.is_elevenlabs_enabled()
if elevenlabs_enabled:
    print("✅ ElevenLabs integration enabled")
    
    # Initialize ElevenLabs services
    try:
        from app.services.elevenlabs_agent_service import ElevenLabsAgentService
        from app.services.elevenlabs_conversation_service import ElevenLabsConversationService
        from app.services.voice_service import VoiceService
        
        elevenlabs_config = config_service.get_elevenlabs_config()
        voice_service = VoiceService(elevenlabs_config)
        elevenlabs_agent_service = ElevenLabsAgentService(elevenlabs_config, voice_service)
        elevenlabs_conversation_service = ElevenLabsConversationService(elevenlabs_config)
        
        print("✅ ElevenLabs conversational AI services initialized")
    except Exception as e:
        print(f"⚠️  ElevenLabs conversational AI initialization failed: {e}")
        elevenlabs_agent_service = None
        elevenlabs_conversation_service = None
else:
    print("⚠️  ElevenLabs integration disabled or not configured")

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
        "service": "ultravox-twilio-interface",
        "message": "Service is running"
    }

@app.get("/api/v1/health/detailed")
async def detailed_health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "ultravox-twilio-interface",
        "checks": {
            "ultravox_api": "ok",
            "twilio_api": "ok"
        },
        "message": "All services are healthy"
    }

@app.post("/api/v1/agents")
async def create_agent(agent_data: dict):
    """Create an agent."""
    try:
        print(f"Creating agent: {agent_data}")
        
        # Initialize agent service if not already done
        global agent_service
        if not agent_service:
            agent_service = AgentService(http_client, config_service)
        
        agent_config = AgentConfig(
            name=agent_data["name"],
            prompt=agent_data["prompt"],
            voice=agent_data.get("voice", "9dc1c0e9-db7c-46a5-a610-b04e7ebf37ee")
        )
        
        agent = await agent_service.create_agent(agent_config)
        
        return {
            "id": agent.id,
            "config": {
                "name": agent.config.name,
                "prompt": agent.config.prompt,
                "voice": agent.config.voice
            },
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "status": "active"
        }
        
    except Exception as e:
        print(f"Error creating agent: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/agents")
async def list_agents():
    """List all agents."""
    try:
        # Initialize agent service if not already done
        global agent_service
        if not agent_service:
            agent_service = AgentService(http_client, config_service)
        
        agents = await agent_service.list_agents()
        
        return [{
            "id": agent.id,
            "config": {
                "name": agent.config.name,
                "prompt": agent.config.prompt,
                "voice": agent.config.voice
            },
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "status": "active"
        } for agent in agents]
        
    except Exception as e:
        print(f"Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/voices")
async def list_voices():
    """List available ElevenLabs voices."""
    if not voice_service:
        raise HTTPException(status_code=503, detail="ElevenLabs voice service not available")
    
    try:
        print("📋 Listing ElevenLabs voices...")
        
        # Use the global voice_service instance
        voices = await voice_service.list_voices()
        
        voice_list = [{
            "voice_id": voice.voice_id,
            "name": voice.name,
            "category": voice.category,
            "description": voice.description,
            "preview_url": voice.preview_url,
            "labels": voice.labels
        } for voice in voices]
        
        print(f"✅ Successfully listed {len(voice_list)} voices")
        return voice_list
            
    except Exception as e:
        print(f"❌ Error listing voices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/voices/{voice_id}/preview")
async def preview_voice(voice_id: str):
    """Generate a preview of a specific voice."""
    if not voice_service:
        raise HTTPException(status_code=503, detail="ElevenLabs voice service not available")
    
    try:
        print(f"🔊 Generating voice preview for {voice_id}...")
        
        # Use the global voice_service instance
        audio_data = await voice_service.preview_voice(voice_id)
        
        print(f"✅ Successfully generated voice preview ({audio_data.size_bytes} bytes)")
        
        # Return audio as streaming response
        from fastapi.responses import Response
        return Response(
            content=audio_data.content,
            media_type=audio_data.content_type,
            headers={
                "Content-Disposition": f"inline; filename=preview_{voice_id}.mp3",
                "Content-Length": str(audio_data.size_bytes)
            }
        )
        
    except Exception as e:
        print(f"❌ Error generating voice preview: {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Voice {voice_id} not found")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/calls/elevenlabs")
async def make_elevenlabs_call(call_data: dict):
    """Make an ElevenLabs text-to-speech call."""
    if not elevenlabs_enabled:
        raise HTTPException(status_code=503, detail="ElevenLabs integration is not enabled")
    
    try:
        print(f"🎤 Creating ElevenLabs call: {call_data}")
        
        # Validate request data
        elevenlabs_request = ElevenLabsCallRequest(
            phone_number=call_data["phone_number"],
            text=call_data["text"],
            voice_id=call_data["voice_id"],
            voice_settings=call_data.get("voice_settings"),
            template_context=call_data.get("template_context", {})
        )
        
        # Initialize services
        elevenlabs_config = config_service.get_elevenlabs_config()
        voice_service_instance = VoiceService(elevenlabs_config)
        
        # Generate speech
        print(f"🎵 Generating speech with voice {elevenlabs_request.voice_id}...")
        from app.models.elevenlabs import VoiceSettings
        
        # Convert voice_settings dict to VoiceSettings object if provided
        voice_settings = None
        if elevenlabs_request.voice_settings:
            voice_settings = VoiceSettings(**elevenlabs_request.voice_settings)
        
        audio_data = await voice_service_instance.generate_speech(
            text=elevenlabs_request.text,
            voice_id=elevenlabs_request.voice_id,
            voice_settings=voice_settings
        )
        
        print(f"✅ Speech generated ({audio_data.size_bytes} bytes)")
        
        # Save audio temporarily for Twilio
        temp_audio_path = await voice_service_instance.save_audio_temporarily(audio_data)
        
        try:
            # Initialize call service if not already done
            global call_service
            if not call_service:
                call_service = CallService(config_service, http_client)
            
            # Create a call with the generated audio
            call_result = await call_service.create_elevenlabs_call(
                elevenlabs_request, 
                temp_audio_path
            )
            
            print(f"✅ ElevenLabs call created successfully: {call_result.call_sid}")
            
            return {
                "call_sid": call_result.call_sid,
                "status": call_result.status,
                "phone_number": call_result.phone_number,
                "voice_id": elevenlabs_request.voice_id,
                "text_length": len(elevenlabs_request.text),
                "audio_duration_estimate": voice_service_instance._estimate_duration(elevenlabs_request.text)
            }
            
        finally:
            # Clean up temporary file
            voice_service_instance.cleanup_temporary_file(temp_audio_path)
        
    except Exception as e:
        print(f"Error making ElevenLabs call: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/calls/unified")
async def make_unified_call(call_data: dict):
    """Make a unified call (either Ultravox or ElevenLabs)."""
    try:
        print(f"Making unified call: {call_data}")
        
        # Validate unified request
        unified_request = UnifiedCallRequest(**call_data)
        
        if unified_request.call_type == "ultravox":
            # Route to Ultravox
            return await make_call(unified_request.agent_id, {
                "phone_number": unified_request.phone_number,
                "template_context": unified_request.template_context
            })
        elif unified_request.call_type == "elevenlabs":
            # Route to ElevenLabs
            return await make_elevenlabs_call({
                "phone_number": unified_request.phone_number,
                "text": unified_request.text,
                "voice_id": unified_request.voice_id,
                "voice_settings": unified_request.voice_settings,
                "template_context": unified_request.template_context
            })
        else:
            raise HTTPException(status_code=400, detail=f"Unknown call type: {unified_request.call_type}")
            
    except Exception as e:
        print(f"Error making unified call: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/calls/{agent_id}")
async def make_call(agent_id: str, call_data: dict):
    """Make a call."""
    try:
        print(f"Making call with agent {agent_id}: {call_data}")
        
        # Initialize call service if not already done
        global call_service
        if not call_service:
            call_service = CallService(config_service, http_client)
        
        call_request = CallRequest(
            phone_number=call_data["phone_number"],
            agent_id=agent_id,
            template_context=call_data.get("template_context", {})
        )
        
        call_result = await call_service.initiate_call(call_request)
        
        return {
            "call_sid": call_result.call_sid,
            "join_url": call_result.join_url,
            "status": call_result.status,
            "created_at": call_result.created_at.isoformat(),
            "call_type": "ultravox",
            "agent_id": agent_id,
            "phone_number": call_data["phone_number"]
        }
        
    except Exception as e:
        print(f"Error making call: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# ElevenLabs Conversational AI Endpoints
# ============================================================================

@app.post("/api/v1/agents/elevenlabs")
async def create_elevenlabs_agent(agent_data: dict):
    """Create an ElevenLabs conversational agent."""
    if not elevenlabs_agent_service:
        raise HTTPException(
            status_code=503, 
            detail="ElevenLabs conversational AI service not available"
        )
    
    try:
        print(f"🤖 Creating ElevenLabs agent: {agent_data}")
        
        from app.models.elevenlabs import ElevenLabsAgentConfig
        
        # Validate and create agent config
        agent_config = ElevenLabsAgentConfig(
            name=agent_data["name"],
            system_prompt=agent_data["system_prompt"],
            voice_id=agent_data["voice_id"],
            template_variables=agent_data.get("template_variables", {})
        )
        
        # Create agent
        agent = await elevenlabs_agent_service.create_agent(agent_config)
        
        print(f"✅ Successfully created ElevenLabs agent: {agent.id}")
        
        return {
            "id": agent.id,
            "name": agent.config.name,
            "agent_type": "elevenlabs",
            "voice_id": agent.config.voice_id,
            "status": agent.status,
            "created_at": agent.created_at.isoformat(),
            "config": {
                "name": agent.config.name,
                "system_prompt": agent.config.system_prompt,
                "voice_id": agent.config.voice_id,
                "template_variables": agent.config.template_variables
            }
        }
        
    except Exception as e:
        print(f"❌ Error creating ElevenLabs agent: {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "validation" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents/elevenlabs")
async def list_elevenlabs_agents():
    """List ElevenLabs conversational agents."""
    if not elevenlabs_agent_service:
        raise HTTPException(
            status_code=503, 
            detail="ElevenLabs conversational AI service not available"
        )
    
    try:
        print("📋 Listing ElevenLabs agents...")
        
        agents = await elevenlabs_agent_service.list_agents()
        
        agent_list = []
        for agent in agents:
            agent_list.append({
                "id": agent.id,
                "name": agent.config.name,
                "agent_type": "elevenlabs",
                "voice_id": agent.config.voice_id,
                "status": agent.status,
                "created_at": agent.created_at.isoformat(),
                "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
            })
        
        print(f"✅ Successfully listed {len(agent_list)} ElevenLabs agents")
        return agent_list
        
    except Exception as e:
        print(f"❌ Error listing ElevenLabs agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/calls/elevenlabs/{agent_id}")
async def create_elevenlabs_conversational_call(agent_id: str, call_data: dict):
    """Create an ElevenLabs conversational AI call."""
    if not elevenlabs_conversation_service or not call_service:
        raise HTTPException(
            status_code=503, 
            detail="ElevenLabs conversational AI service not available"
        )
    
    try:
        print(f"📞 Creating ElevenLabs conversational call with agent: {agent_id}")
        
        from app.models.elevenlabs import ElevenLabsConversationalCallRequest
        
        # Validate request data
        elevenlabs_request = ElevenLabsConversationalCallRequest(
            phone_number=call_data["phone_number"],
            agent_id=agent_id,
            template_context=call_data.get("template_context", {})
        )
        
        # Initialize call service with ElevenLabs conversation service if needed
        if not call_service.elevenlabs_conversation_service:
            call_service.elevenlabs_conversation_service = elevenlabs_conversation_service
        
        # Create conversational call
        call_result = await call_service._initiate_elevenlabs_conversational_call(elevenlabs_request)
        
        print(f"✅ ElevenLabs conversational call created successfully: {call_result.call_sid}")
        
        return {
            "call_sid": call_result.call_sid,
            "status": call_result.status,
            "agent_id": agent_id,
            "phone_number": call_result.phone_number,
            "call_type": "elevenlabs_conversational",
            "created_at": call_result.created_at.isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error creating ElevenLabs conversational call: {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "validation" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/agents")
async def create_ultravox_agent(agent_data: dict):
    """Create an Ultravox agent."""
    if not agent_service:
        raise HTTPException(
            status_code=503, 
            detail="Ultravox agent service not available"
        )
    
    try:
        print(f"🤖 Creating Ultravox agent: {agent_data}")
        
        from app.models.agent import AgentConfig
        
        # Validate and create agent config
        agent_config = AgentConfig(
            name=agent_data["name"],
            prompt=agent_data["prompt"],
            voice=agent_data.get("voice", "default"),
            language=agent_data.get("language", "en"),
            template_variables=agent_data.get("template_variables", {})
        )
        
        # Create agent
        agent = await agent_service.create_agent(agent_config)
        
        print(f"✅ Successfully created Ultravox agent: {agent.id}")
        
        return {
            "id": agent.id,
            "config": {
                "name": agent.config.name,
                "prompt": agent.config.prompt,
                "voice": agent.config.voice,
                "language": agent.config.language,
                "template_variables": agent.config.template_variables
            },
            "status": agent.status,
            "created_at": agent.created_at.isoformat(),
            "updated_at": agent.updated_at.isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error creating Ultravox agent: {str(e)}")
        if "validation" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/calls/{agent_id}")
async def create_ultravox_call(agent_id: str, call_data: dict):
    """Create an Ultravox call."""
    if not call_service:
        raise HTTPException(
            status_code=503, 
            detail="Call service not available"
        )
    
    try:
        print(f"📞 Creating Ultravox call with agent: {agent_id}")
        
        from app.models.call import CallRequest
        
        # Validate request data
        call_request = CallRequest(
            phone_number=call_data["phone_number"],
            agent_id=agent_id,
            template_context=call_data.get("template_context", {})
        )
        
        # Create call
        call_result = await call_service.initiate_call(call_request)
        
        print(f"✅ Ultravox call created successfully: {call_result.call_sid}")
        
        return {
            "call_sid": call_result.call_sid,
            "status": call_result.status,
            "agent_id": agent_id,
            "phone_number": call_result.phone_number,
            "call_type": "ultravox",
            "created_at": call_result.created_at.isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error creating Ultravox call: {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "validation" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents")
async def list_all_agents():
    """List all agents from both Ultravox and ElevenLabs platforms."""
    try:
        print("📋 Listing all agents from both platforms...")
        
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
            else:
                print("⚠️ Ultravox agent service not available")
        except Exception as e:
            print(f"⚠️ Failed to load Ultravox agents: {str(e)}")
            # Don't fail the entire request, just skip Ultravox agents
        
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
                        "created_at": agent.created_at.isoformat(),
                        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
                    })
            else:
                print("⚠️ ElevenLabs agent service not available")
        except Exception as e:
            print(f"⚠️ Failed to load ElevenLabs agents: {str(e)}")
            # Don't fail the entire request, just skip ElevenLabs agents
        
        print(f"✅ Successfully listed {len(all_agents)} agents from both platforms")
        
        # Return results even if empty
        return {
            "agents": all_agents,
            "total_count": len(all_agents),
            "ultravox_count": len([a for a in all_agents if a["agent_type"] == "ultravox"]),
            "elevenlabs_count": len([a for a in all_agents if a["agent_type"] == "elevenlabs"])
        }
        
    except Exception as e:
        print(f"❌ Error listing all agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    
    print("🚀 Starting Ultravox-Twilio Web Interface...")
    print(f"📱 Web Interface: http://localhost:{port}")
    print(f"🔍 Health Check: http://localhost:{port}/api/v1/health")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
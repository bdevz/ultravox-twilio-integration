#!/usr/bin/env python3
"""
Demo script showing how to use the new ElevenLabs Conversational AI models.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.models.elevenlabs import (
    # Conversational AI models
    ElevenLabsAgentConfig,
    ElevenLabsAgent,
    ElevenLabsAgentStatus,
    ElevenLabsConversation,
    ConversationStatus,
    ElevenLabsConversationalCallRequest,
    ElevenLabsCallResult,
    ElevenLabsConversationConfig,
    TurnDetectionConfig,
    UnifiedAgent,
    UnifiedCallRequest,
    # Configuration
    ElevenLabsConfig,
    VoiceSettings
)


def demo_turn_detection_config():
    """Demonstrate TurnDetectionConfig usage."""
    print("🔧 Turn Detection Configuration")
    print("=" * 40)
    
    # Create custom turn detection config
    turn_detection = TurnDetectionConfig(
        type="server_vad",
        threshold=0.7,
        prefix_padding_ms=400,
        silence_duration_ms=1200
    )
    
    print(f"Type: {turn_detection.type}")
    print(f"Threshold: {turn_detection.threshold}")
    print(f"Prefix Padding: {turn_detection.prefix_padding_ms}ms")
    print(f"Silence Duration: {turn_detection.silence_duration_ms}ms")
    
    # Convert to ElevenLabs API format
    api_format = turn_detection.to_elevenlabs_dict()
    print(f"API Format: {api_format}")
    print()


def demo_conversation_config():
    """Demonstrate ElevenLabsConversationConfig usage."""
    print("💬 Conversation Configuration")
    print("=" * 40)
    
    # Create conversation config with custom settings
    conversation_config = ElevenLabsConversationConfig(
        turn_detection=TurnDetectionConfig(threshold=0.8),
        language="en-US",
        max_duration_seconds=2400,  # 40 minutes
        agent_tools=[
            {"type": "function", "name": "get_weather"},
            {"type": "function", "name": "book_appointment"}
        ],
        webhook_url="https://myapp.com/webhook"
    )
    
    print(f"Language: {conversation_config.language}")
    print(f"Max Duration: {conversation_config.max_duration_seconds} seconds")
    print(f"Agent Tools: {len(conversation_config.agent_tools)} tools")
    print(f"Webhook URL: {conversation_config.webhook_url}")
    
    # Convert to ElevenLabs API format
    api_format = conversation_config.to_elevenlabs_dict()
    print(f"API Format Keys: {list(api_format.keys())}")
    print()


def demo_agent_config():
    """Demonstrate ElevenLabsAgentConfig usage."""
    print("🤖 Agent Configuration")
    print("=" * 40)
    
    # Create agent configuration
    agent_config = ElevenLabsAgentConfig(
        name="Customer Support Agent",
        system_prompt="""You are a helpful customer support agent for Acme Corp. 
        You should be friendly, professional, and knowledgeable about our products.
        Always greet customers by name if provided in the template variables.""",
        voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel voice
        conversation_config=ElevenLabsConversationConfig(
            language="en-US",
            max_duration_seconds=1800
        ),
        template_variables={
            "company_name": "Acme Corp",
            "support_hours": "9 AM - 5 PM EST",
            "phone_number": "1-800-ACME-HELP"
        }
    )
    
    print(f"Name: {agent_config.name}")
    print(f"Voice ID: {agent_config.voice_id}")
    print(f"Prompt Length: {len(agent_config.system_prompt)} characters")
    print(f"Template Variables: {list(agent_config.template_variables.keys())}")
    
    # Convert to ElevenLabs API format
    api_format = agent_config.to_elevenlabs_dict()
    print(f"API Format Keys: {list(api_format.keys())}")
    print()


def demo_agent_creation():
    """Demonstrate ElevenLabsAgent creation."""
    print("👤 Agent Creation")
    print("=" * 40)
    
    # Create agent configuration
    config = ElevenLabsAgentConfig(
        name="Sales Assistant",
        system_prompt="You are a knowledgeable sales assistant who helps customers find the right products.",
        voice_id="EXAVITQu4vr4xnSDxMaL",  # Bella voice
        template_variables={"product_catalog": "electronics"}
    )
    
    # Create agent instance
    agent = ElevenLabsAgent(
        id="agent_sales_001",
        config=config,
        created_at=datetime.now(timezone.utc),
        status=ElevenLabsAgentStatus.ACTIVE
    )
    
    print(f"Agent ID: {agent.id}")
    print(f"Agent Type: {agent.agent_type}")
    print(f"Status: {agent.status}")
    print(f"Created: {agent.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Voice Info: {agent.voice_info}")
    print()


def demo_conversation_management():
    """Demonstrate conversation management."""
    print("💭 Conversation Management")
    print("=" * 40)
    
    # Create conversation
    conversation = ElevenLabsConversation(
        id="conv_12345",
        agent_id="agent_sales_001",
        status=ConversationStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        phone_number="+1234567890",
        metadata={"customer_id": "cust_789", "priority": "high"}
    )
    
    print(f"Conversation ID: {conversation.id}")
    print(f"Agent ID: {conversation.agent_id}")
    print(f"Status: {conversation.status}")
    print(f"Is Active: {conversation.is_active}")
    print(f"Phone Number: {conversation.phone_number}")
    print(f"Metadata: {conversation.metadata}")
    print()


def demo_call_requests():
    """Demonstrate call request models."""
    print("📞 Call Requests")
    print("=" * 40)
    
    # ElevenLabs conversational call request
    elevenlabs_request = ElevenLabsConversationalCallRequest(
        phone_number="+1234567890",
        agent_id="agent_sales_001",
        template_context={
            "customer_name": "John Smith",
            "account_type": "premium"
        }
    )
    
    print("ElevenLabs Call Request:")
    print(f"  Phone: {elevenlabs_request.phone_number}")
    print(f"  Agent: {elevenlabs_request.agent_id}")
    print(f"  Context: {elevenlabs_request.template_context}")
    print()
    
    # Unified call request
    unified_request = UnifiedCallRequest(
        call_type="elevenlabs",
        phone_number="+1234567890",
        agent_id="agent_sales_001",
        template_context={"user_name": "Jane Doe"}
    )
    
    print("Unified Call Request:")
    print(f"  Type: {unified_request.call_type}")
    print(f"  Phone: {unified_request.phone_number}")
    print(f"  Agent: {unified_request.agent_id}")
    print(f"  Context: {unified_request.template_context}")
    print()


def demo_unified_agent():
    """Demonstrate unified agent model."""
    print("🔄 Unified Agent Model")
    print("=" * 40)
    
    # Create ElevenLabs agent
    config = ElevenLabsAgentConfig(
        name="Unified Demo Agent",
        system_prompt="You are a demo agent for testing unified functionality.",
        voice_id="21m00Tcm4TlvDq8ikWAM"
    )
    
    elevenlabs_agent = ElevenLabsAgent(
        id="agent_unified_001",
        config=config,
        created_at=datetime.now(timezone.utc),
        status=ElevenLabsAgentStatus.ACTIVE
    )
    
    # Convert to unified format
    unified_agent = UnifiedAgent.from_elevenlabs_agent(
        elevenlabs_agent, 
        voice_name="Rachel"
    )
    
    print(f"Unified Agent ID: {unified_agent.id}")
    print(f"Name: {unified_agent.name}")
    print(f"Type: {unified_agent.agent_type}")
    print(f"Status: {unified_agent.status}")
    print(f"Voice Info: {unified_agent.voice_info}")
    print(f"Config Keys: {list(unified_agent.config.keys())}")
    print()


def demo_configuration():
    """Demonstrate ElevenLabs configuration."""
    print("⚙️  ElevenLabs Configuration")
    print("=" * 40)
    
    # Create configuration with conversational AI settings
    config = ElevenLabsConfig(
        api_key="sk-test-key-12345",
        base_url="https://api.elevenlabs.io",
        default_voice_id="21m00Tcm4TlvDq8ikWAM",
        enable_conversational_ai=True,
        default_conversation_config=ElevenLabsConversationConfig(
            language="en-US",
            max_duration_seconds=2400
        )
    )
    
    print(f"API Key: {config.api_key[:10]}...")
    print(f"Base URL: {config.base_url}")
    print(f"Default Voice: {config.default_voice_id}")
    print(f"Conversational AI Enabled: {config.enable_conversational_ai}")
    print(f"Default Max Duration: {config.default_conversation_config.max_duration_seconds}s")
    print()


def main():
    """Run all demonstrations."""
    print("🎉 ElevenLabs Conversational AI Models Demo")
    print("=" * 50)
    print()
    
    demo_turn_detection_config()
    demo_conversation_config()
    demo_agent_config()
    demo_agent_creation()
    demo_conversation_management()
    demo_call_requests()
    demo_unified_agent()
    demo_configuration()
    
    print("✅ Demo completed successfully!")
    print("\nThese models provide the foundation for:")
    print("  • Creating and managing ElevenLabs conversational AI agents")
    print("  • Configuring conversation settings and turn detection")
    print("  • Managing conversation lifecycle and phone integration")
    print("  • Unified handling of both Ultravox and ElevenLabs agents")
    print("  • Type-safe API requests and responses")


if __name__ == "__main__":
    main()
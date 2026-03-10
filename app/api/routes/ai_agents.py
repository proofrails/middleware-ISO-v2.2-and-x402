"""AI-powered command parsing for agents."""
from fastapi import APIRouter, Depends, HTTPException

from app import ai

router = APIRouter(tags=["ai-agents"])


@router.post("/v1/ai/parse-command")
async def parse_command_with_ai(payload: dict):
    """Parse natural language command using system AI.
    
    This endpoint uses the shared system OpenAI API to parse
    natural language commands into structured actions.
    
    Users can optionally provide custom system prompts to
    customize the AI's behavior for their use case.
    """
    message = payload.get("message")
    system_prompt = payload.get("system_prompt")
    
    if not message:
        raise HTTPException(400, "message_required")
    
    # Default system prompt for command parsing
    default_prompt = """You are a command parser for an ISO 20022 payment middleware.
Parse user messages into structured commands with this format:
{
  "action": "list|get|verify|statement|refund|help",
  "args": {...}
}

Available actions:
- list: List receipts. Args: { limit: number }
- get: Get receipt. Args: { receiptId: string }
- verify: Verify bundle. Args: { bundleUrl: string }
- statement: Generate statement. Args: { date: string }
- refund: Initiate refund. Args: { receiptId: string, reason: string }
- help: Show help

Examples:
"show me 5 receipts" → {"action":"list","args":{"limit":5}}
"verify this bundle https://..." → {"action":"verify","args":{"bundleUrl":"https://..."}}
"refund receipt abc123 because duplicate" → {"action":"refund","args":{"receiptId":"abc123","reason":"duplicate"}}

Only return the JSON object, nothing else."""

    prompt = system_prompt or default_prompt
    
    try:
        # Use existing AI module to parse command
        import json
        
        response = await ai.send_message(
            message=message,
            system=prompt,
            model="gpt-4o-mini",
            temperature=0.2,
        )
        
        # Parse JSON response
        try:
            parsed = json.loads(response)
            return {
                "success": True,
                "parsed_command": parsed,
                "original_message": message,
            }
        except json.JSONDecodeError:
            # AI didn't return valid JSON, try to extract
            return {
                "success": False,
                "error": "AI response was not valid JSON",
                "raw_response": response,
                "original_message": message,
            }
    
    except Exception as e:
        raise HTTPException(500, f"AI parsing failed: {str(e)}")


@router.post("/v1/agents/{agent_id}/test-ai")
async def test_agent_ai(agent_id: str, payload: dict):
    """Test AI parsing for a specific agent configuration."""
    from app.api.deps import get_session
    from sqlalchemy.orm import Session
    from fastapi import Depends
    from app import models
    
    session = next(get_session())
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    test_message = payload.get("test_message", "list 5 receipts")
    
    # Parse based on agent's AI mode
    if agent.ai_mode == "simple":
        return {
            "mode": "simple",
            "message": "AI not enabled - using simple parsing",
            "test_message": test_message,
        }
    
    # Use shared or custom AI
    result = await parse_command_with_ai({
        "message": test_message,
        "system_prompt": agent.ai_system_prompt,
    })
    
    return {
        "mode": agent.ai_mode,
        "test_message": test_message,
        "parsed_result": result,
        "ai_provider": agent.ai_provider or "system",
        "ai_model": agent.ai_model or "gpt-4o-mini",
    }

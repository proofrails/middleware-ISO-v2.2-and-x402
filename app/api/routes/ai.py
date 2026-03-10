from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from app import ai as ai_srv
from app.api.deps import get_session
from app.auth import Principal, resolve_principal

router = APIRouter(tags=["ai"])


@router.post("/v1/ai/assist")
def ai_assist(payload: dict, session=Depends(get_session), principal: Principal = Depends(resolve_principal)):
    """Scoped AI assistant.

    IMPORTANT: principal is resolved here and must be passed down so that
    project keys cannot read other projects' receipts via the AI tools.
    """

    try:
        return ai_srv.assist(payload, session, principal=principal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ai_assist_failed: {e}")


@router.get("/v1/ai/status")
def ai_status(principal: Principal = Depends(resolve_principal)):
    """Return AI provider configuration status.
    
    Shows whether AI is enabled, which provider/model is configured,
    and basic configuration info for UX purposes.
    """
    provider = (os.getenv("AI_PROVIDER") or "").strip().lower()
    model = os.getenv("AI_MODEL") or ""
    
    enabled = bool(provider)
    provider_name = provider if provider else "none"
    
    # Check if required API keys are present (without exposing them)
    has_api_key = False
    if provider == "openai":
        has_api_key = bool(os.getenv("OPENAI_API_KEY"))
        if not model:
            model = "gpt-4o-mini"
    elif provider == "anthropic":
        has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    return {
        "enabled": enabled and has_api_key,
        "provider": provider_name,
        "model": model or "(not configured)",
        "has_api_key": has_api_key,
        "features": {
            "scope_enforcement": True,
            "receipt_tools": True,
            "sdk_help": True,
            "verification": True,
        }
    }

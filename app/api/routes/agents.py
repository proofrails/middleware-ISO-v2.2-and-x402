"""Agent management endpoints for x402-powered autonomous agents."""
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_session
from app.auth.principal import Principal
from app.auth.api_key_auth import resolve_principal

router = APIRouter(tags=["agents"])


@router.post("/v1/agents")
def register_agent(
    payload: dict,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Register a new autonomous agent."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    name = payload.get("name")
    wallet_address = payload.get("wallet_address")
    
    if not name or not wallet_address:
        raise HTTPException(400, "name_and_wallet_required")
    
    agent = models.AgentConfig(
        id=uuid4(),
        name=name,
        wallet_address=wallet_address,
        xmtp_address=payload.get("xmtp_address"),
        pricing_rules=payload.get("pricing_rules") or {},
        status="active",
        project_id=principal.project_id,
    )
    
    session.add(agent)
    session.commit()
    session.refresh(agent)
    
    return {
        "id": str(agent.id),
        "name": agent.name,
        "wallet_address": agent.wallet_address,
        "status": agent.status,
    }


@router.get("/v1/agents")
def list_agents(
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """List all agents for current project."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    query = session.query(models.AgentConfig)
    
    # Filter by project if not admin
    if not principal.is_admin and principal.project_id:
        query = query.filter_by(project_id=principal.project_id)
    
    agents = query.all()
    
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "wallet_address": a.wallet_address,
            "xmtp_address": a.xmtp_address,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in agents
    ]


@router.get("/v1/agents/{agent_id}")
def get_agent(
    agent_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Get agent details."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    # Check ownership
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    return {
        "id": str(agent.id),
        "name": agent.name,
        "wallet_address": agent.wallet_address,
        "xmtp_address": agent.xmtp_address,
        "pricing_rules": agent.pricing_rules,
        "status": agent.status,
        "project_id": str(agent.project_id) if agent.project_id else None,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


@router.put("/v1/agents/{agent_id}")
def update_agent(
    agent_id: str,
    payload: dict,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Update agent configuration."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    # Update fields
    if "name" in payload:
        agent.name = payload["name"]
    if "status" in payload:
        agent.status = payload["status"]
    if "pricing_rules" in payload:
        agent.pricing_rules = payload["pricing_rules"]
    if "xmtp_address" in payload:
        agent.xmtp_address = payload["xmtp_address"]
    
    from datetime import datetime
    agent.updated_at = datetime.utcnow()
    
    session.commit()
    session.refresh(agent)
    
    return {"id": str(agent.id), "status": "updated"}


@router.delete("/v1/agents/{agent_id}")
def delete_agent(
    agent_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Delete an agent."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    session.delete(agent)
    session.commit()
    
    return {"id": agent_id, "status": "deleted"}


@router.get("/v1/agents/{agent_id}/stats")
def get_agent_stats(
    agent_id: str,
    days: int = 7,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Get agent usage statistics and revenue."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    # Get payments from this agent
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    since = datetime.utcnow() - timedelta(days=days)
    
    payments = (
        session.query(models.X402Payment)
        .filter(models.X402Payment.agent_id == agent_id)
        .filter(models.X402Payment.verified_at >= since)
        .all()
    )
    
    total_spent = sum(p.amount for p in payments)
    
    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "days": days,
        "payment_count": len(payments),
        "total_spent": str(total_spent),
        "payments": [
            {
                "tx_hash": p.tx_hash,
                "amount": str(p.amount),
                "endpoint": p.endpoint,
                "verified_at": p.verified_at.isoformat() if p.verified_at else None,
            }
            for p in payments
        ],
    }


@router.post("/v1/agents/{agent_id}/test")
def test_agent(
    agent_id: str,
    payload: dict,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Test agent interaction (simulate a command)."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    command = payload.get("command", "")
    
    from datetime import datetime
    
    # Simple echo test
    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "command_received": command,
        "response": f"Agent {agent.name} received: {command}",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.put("/v1/agents/{agent_id}/ai-config")
def update_ai_config(
    agent_id: str,
    payload: dict,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Update agent AI configuration."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    # Update AI config fields
    if "ai_mode" in payload:
        agent.ai_mode = payload["ai_mode"]
    if "ai_system_prompt" in payload:
        agent.ai_system_prompt = payload["ai_system_prompt"]
    if "ai_provider" in payload:
        agent.ai_provider = payload["ai_provider"]
    if "ai_model" in payload:
        agent.ai_model = payload["ai_model"]
    if "ai_endpoint" in payload:
        agent.ai_endpoint = payload["ai_endpoint"]
    
    # Handle API key encryption
    if "ai_api_key" in payload and payload["ai_api_key"]:
        # Simple base64 encoding (in production, use proper encryption)
        import base64
        encrypted_key = base64.b64encode(payload["ai_api_key"].encode()).decode()
        agent.ai_api_key_encrypted = encrypted_key
    
    from datetime import datetime
    agent.updated_at = datetime.utcnow()
    
    session.commit()
    session.refresh(agent)
    
    return {"id": str(agent.id), "status": "ai_config_updated"}


@router.post("/v1/agents/{agent_id}/download-template")
def download_agent_template(
    agent_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
):
    """Generate and download a personalized agent package."""
    if principal.is_public:
        raise HTTPException(401, "auth_required")
    
    agent = session.get(models.AgentConfig, agent_id)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    
    if not principal.is_admin and agent.project_id != principal.project_id:
        raise HTTPException(403, "access_denied")
    
    # Generate agent package ZIP
    import io
    from zipfile import ZipFile, ZIP_DEFLATED
    import os
    
    buf = io.BytesIO()
    
    # Get API base URL
    api_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    
    # Generate .env file
    env_content = f"""# XMTP Agent Configuration
XMTP_ENV=dev
WALLET_PRIVATE_KEY=your_private_key_here

# ISO Middleware API
ISO_MW_API_URL={api_url}
ISO_MW_API_KEY=your_api_key_here

# x402 Payment Configuration
X402_RECIPIENT=0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8
CHAIN_RPC_URL=https://mainnet.base.org
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Agent Settings
AGENT_NAME={agent.name}
AGENT_ID={agent.id}

# AI Configuration
AI_MODE={agent.ai_mode or 'simple'}
AI_SYSTEM_PROMPT={agent.ai_system_prompt or ''}
AI_PROVIDER={agent.ai_provider or 'openai'}
AI_MODEL={agent.ai_model or 'gpt-4o-mini'}

LOG_LEVEL=info
"""
    
    readme = f"""# {agent.name} - XMTP Agent

This is your personalized ISO Middleware XMTP agent.

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure your wallet:
   - Edit `.env`
   - Add your `WALLET_PRIVATE_KEY`
   - Add your `ISO_MW_API_KEY`

3. Run the agent:
   ```bash
   npm run build
   npm start
   ```

4. Test via XMTP:
   - Use Converse app or any XMTP client
   - Send message to: {agent.wallet_address}
   - Try: "help" to see available commands

## AI Mode: {agent.ai_mode}

{"✅ Simple - No AI, exact commands only" if agent.ai_mode == 'simple' else ""}
{"✅ Shared - Uses system AI (FREE)" if agent.ai_mode == 'shared' else ""}
{"✅ Custom - Uses your AI API key" if agent.ai_mode == 'custom' else ""}

## Deployment

See docs/AGENTS_GUIDE.md for full deployment options:
- PM2 (recommended)
- Docker
- Railway/Heroku

## Support

- API: {api_url}/docs
- Agent Management: {api_url.replace('api', 'app')}/agents
- Documentation: https://github.com/.../docs/
"""
    
    with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
        # Copy all agent source files from agents/iso-x402-agent/
        base_path = "agents/iso-x402-agent"
        
        # Add generated files
        zf.writestr(".env", env_content)
        zf.writestr("README.md", readme)
        
        # Copy agent source files
        try:
            import os as os_module
            for root, dirs, files in os_module.walk(base_path):
                for file in files:
                    if file in ['.env', '.env.example']:
                        continue
                    file_path = os_module.path.join(root, file)
                    arcname = file_path.replace(base_path + os_module.sep, '')
                    zf.write(file_path, arcname)
        except Exception as e:
            # If files don't exist, just include the env and readme
            pass
    
    buf.seek(0)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={agent.name.replace(' ', '-')}-agent.zip"
        },
    )

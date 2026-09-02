"""
PHANTOM AI Copilot — API Endpoints
Provides dedicated /copilot/chat, /copilot/confirm, /copilot/tools, /copilot/context, and /copilot/health.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.copilot import get_global_copilot_agent, CopilotChatResponse
from app.ai.agents.tool_registry import phantom_tool_registry
from app.api.deps_auth import Principal, get_principal, require_camera_view
from app.db.dependencies import get_db

router = APIRouter(prefix="/copilot", tags=["PHANTOM AI Autonomous Copilot"])


class CopilotChatRequest(BaseModel):
    query: str = Field(..., description="Natural language surveillance command or question (Hindi, Gujarati, English, Marathi, Hinglish)")
    session_id: Optional[str] = Field(None, description="Client session ID for multi-turn conversational memory")
    current_route: Optional[str] = Field(None, description="Current frontend view/page e.g. 'dashboard', 'live_monitoring'")
    selected_camera_id: Optional[str] = Field(None, description="Currently selected camera ID in UI context")


class CopilotConfirmRequest(BaseModel):
    confirmation_token: str = Field(..., description="Confirmation token for sensitive action")
    action_type: str = Field(..., description="Action to confirm")
    payload: Dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/chat",
    summary="Process Multilingual Copilot Query",
    description="Understands natural language commands across Hindi, Gujarati, Marathi, English, and Hinglish, invokes real PHANTOM tools, and returns grounded findings and UI actions.",
)
async def copilot_chat_endpoint(
    payload: CopilotChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Allow authenticated users or fallback to default POLICE_OFFICER role
):
    agent = get_global_copilot_agent()
    
    # Resolve optional principal or default to officer
    operator_role = "POLICE_OFFICER"
    try:
        principal = await get_principal(request)
        if principal and principal.roles:
            operator_role = principal.roles[0]
    except Exception:
        operator_role = "POLICE_OFFICER"

    response: CopilotChatResponse = await agent.process_query(
        query=payload.query,
        session_id=payload.session_id,
        current_route=payload.current_route,
        selected_camera_id=payload.selected_camera_id,
        operator_role=operator_role,
        db_session=db,
    )

    req_id = getattr(request.state, "request_id", None)
    return {
        "success": True,
        "data": {
            "query": response.query,
            "detected_language": response.detected_language,
            "intent": response.intent,
            "text_response": response.text_response,
            "status_steps": [s.__dict__ for s in response.status_steps],
            "ui_actions": [a.__dict__ for a in response.ui_actions],
            "data_card": response.data_card,
            "opened_camera": response.opened_camera,
            "detection_summary": response.detection_summary,
            "session_id": response.session_id,
            "requires_confirmation": response.requires_confirmation,
            "confirmation_payload": response.confirmation_payload,
            "timestamp": response.timestamp,
        },
        "request_id": req_id,
    }


@router.get(
    "/tools",
    summary="List Registered PHANTOM AI Tools",
    description="Returns catalogue of all 40+ approved surveillance tools with security and permission specifications.",
)
async def list_copilot_tools():
    tools = phantom_tool_registry.get_all_tool_definitions()
    return {
        "success": True,
        "total_tools": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "security_level": t.security_level.value,
                "parameters": t.parameters,
                "requires_confirmation": t.requires_confirmation,
            }
            for t in tools
        ],
    }


@router.get(
    "/context",
    summary="Get Dynamic Platform Context Snapshot",
    description="Returns live system-wide telemetry, camera inventory counts, active alert counts, and platform status.",
)
async def get_copilot_context():
    summary = await phantom_tool_registry.get_platform_summary()
    return {
        "success": True,
        "context": summary,
    }


@router.get(
    "/health",
    summary="Get Copilot & AI Subsystem Telemetry",
    description="Real-time status for AI Inference, Streaming Gateway, Camera Catalogue, ANPR OCR, and Database.",
)
async def get_copilot_health():
    health = await phantom_tool_registry.get_system_health()
    return {
        "success": True,
        "health": health,
    }

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database.connection import get_db
from app.services.gemini_service import gemini_service
from app.api.routes.dashboard import get_dashboard_summary

router = APIRouter(prefix="/ai", tags=["AI Solution & Insights"])

class ChatRequest(BaseModel):
    message: str = Field(..., description="Operator query or prompt")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra grid context")

class ChatResponse(BaseModel):
    response: str
    model: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BriefingResponse(BaseModel):
    briefing: str
    model: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@router.post("/chat", response_model=ChatResponse)
def chat_with_copilot(req: ChatRequest, db: Session = Depends(get_db)):
    if not gemini_service.is_configured():
        raise HTTPException(status_code=503, detail="AI Solution is not configured.")

    context = req.context
    if not context:
        try:
            summary = get_dashboard_summary(region="default", db=db)
            context = summary.model_dump() if hasattr(summary, "model_dump") else summary.dict()
        except Exception:
            context = {}

    reply = gemini_service.copilot_chat(req.message, grid_context=context)
    return ChatResponse(response=reply, model=gemini_service.model)

@router.get("/briefing", response_model=BriefingResponse)
def get_grid_briefing(region: str = "default", db: Session = Depends(get_db)):
    if not gemini_service.is_configured():
        raise HTTPException(status_code=503, detail="AI Solution is not configured.")

    try:
        summary = get_dashboard_summary(region=region, db=db)
        data = summary.model_dump() if hasattr(summary, "model_dump") else summary.dict()
    except Exception as e:
        data = {"error": str(e)}

    briefing = gemini_service.generate_grid_briefing(data)
    return BriefingResponse(briefing=briefing, model=gemini_service.model)

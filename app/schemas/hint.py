from datetime import datetime
from pydantic import BaseModel
from app.models.hint import HintStatus, HintCategory, HintPriority


class HintResponse(BaseModel):
    """Response model for a hint"""
    id: int
    device_id: str
    category: HintCategory
    priority: HintPriority
    title: str
    message: str
    status: HintStatus
    created_at: datetime
    shown_at: datetime | None = None
    dismissed_at: datetime | None = None

    class Config:
        from_attributes = True


class HintStatusUpdate(BaseModel):
    """Request model for updating hint status"""
    status: HintStatus


class PendingHintsResponse(BaseModel):
    """Response containing pending hints for a device"""
    hints: list[HintResponse]
    count: int

from datetime import datetime
from pydantic import BaseModel


class UserPreferencesUpdate(BaseModel):
    """Request model for updating user preferences"""
    work_session_minutes: int | None = None
    max_hints_per_hour: int | None = None
    min_minutes_between_hints: int | None = None
    enable_break_reminders: bool | None = None
    enable_app_suggestions: bool | None = None
    enable_workflow_tips: bool | None = None


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences"""
    id: int
    device_id: str
    work_session_minutes: int
    max_hints_per_hour: int
    min_minutes_between_hints: int
    enable_break_reminders: bool
    enable_app_suggestions: bool
    enable_workflow_tips: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

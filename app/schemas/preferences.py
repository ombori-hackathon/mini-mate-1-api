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
    # Time-based hint settings
    break_interval_minutes: int | None = None
    session_duration_minutes: int | None = None
    same_app_threshold_minutes: int | None = None
    enable_same_app_hints: bool | None = None


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
    # Time-based hint settings
    break_interval_minutes: int
    session_duration_minutes: int
    same_app_threshold_minutes: int
    enable_same_app_hints: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

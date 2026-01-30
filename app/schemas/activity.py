from datetime import datetime
from pydantic import BaseModel


class ActivityReportItem(BaseModel):
    """Single activity report item from the client"""
    app_name: str
    window_title: str | None = None      # File name, URL, document title
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    idle_seconds: float | None = None    # Time user has been idle
    might_be_stuck: bool | None = None   # Stuck detection flag

    # App switch tracking
    is_app_switch: bool | None = None
    app_switch_count: int | None = None
    session_minutes: float | None = None

    # Struggle detection
    struggle_score: int | None = None        # 0-10, higher = more struggling
    tab_switch_count: int | None = None      # Tab switches in same app
    back_and_forth_count: int | None = None  # Switching between same 2 apps
    context: str | None = None               # Full context string
    recent_windows: list[str] | None = None  # Recent window titles


class ActivityBatchReport(BaseModel):
    """Batch report containing multiple activities from a device"""
    device_id: str
    activities: list[ActivityReportItem]


class ActivityLogResponse(BaseModel):
    """Response model for stored activity log"""
    id: int
    device_id: str
    app_name: str
    window_title: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: float | None
    idle_seconds: float | None
    might_be_stuck: bool | None
    created_at: datetime

    class Config:
        from_attributes = True

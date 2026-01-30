from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.db import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, nullable=False, index=True)
    work_session_minutes = Column(Integer, default=2)  # 2 min for testing (was 30)
    max_hints_per_hour = Column(Integer, default=20)  # 20 for testing (was 3)
    min_minutes_between_hints = Column(Integer, default=1)  # 1 min for testing (was 10)
    enable_break_reminders = Column(Boolean, default=True)
    enable_app_suggestions = Column(Boolean, default=True)
    enable_workflow_tips = Column(Boolean, default=True)
    # Time-based hint settings
    break_interval_minutes = Column(Integer, default=30)  # Break every X minutes
    session_duration_minutes = Column(Integer, default=60)  # Total session length
    same_app_threshold_minutes = Column(Integer, default=10)  # Hint after X mins in same app
    enable_same_app_hints = Column(Boolean, default=True)  # Toggle same-app hints
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

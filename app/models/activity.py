from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from app.db import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    app_name = Column(String, nullable=False)
    window_title = Column(String, nullable=True)        # File name, URL, etc.
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    idle_seconds = Column(Float, nullable=True)         # Time user was idle
    might_be_stuck = Column(Boolean, nullable=True)     # Stuck detection
    created_at = Column(DateTime, default=datetime.utcnow)

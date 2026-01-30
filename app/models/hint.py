from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
import enum
from app.db import Base


class HintStatus(str, enum.Enum):
    PENDING = "pending"
    SHOWN = "shown"
    DISMISSED = "dismissed"


class HintCategory(str, enum.Enum):
    BREAK_REMINDER = "break_reminder"
    APP_SUGGESTION = "app_suggestion"
    WORKFLOW_TIP = "workflow_tip"
    FOCUS_ALERT = "focus_alert"
    EVENT_REMINDER = "event_reminder"  # For scheduled events


class HintPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Hint(Base):
    __tablename__ = "hints"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    category = Column(Enum(HintCategory), nullable=False)
    priority = Column(Enum(HintPriority), default=HintPriority.MEDIUM)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(HintStatus), default=HintStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    shown_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

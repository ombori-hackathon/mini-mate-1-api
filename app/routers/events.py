from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from app.db import get_db
from app.models.hint import Hint, HintStatus, HintCategory, HintPriority
from app.services.ai_service import ai_service

router = APIRouter(prefix="/events", tags=["events"])


class EventReminderRequest(BaseModel):
    device_id: str
    event_title: str
    event_time: str


@router.post("/reminder")
async def send_event_reminder(
    request: EventReminderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receive an event reminder and generate an AI-powered hint.
    Shows immediately at the scheduled time.
    """

    async def create_event_hint():
        # Generate AI-powered reminder
        hint_result = await ai_service.generate_event_reminder(
            event_title=request.event_title
        )

        if hint_result.should_generate:
            hint = Hint(
                device_id=request.device_id,
                category=HintCategory.EVENT_REMINDER,
                priority=HintPriority.HIGH,
                title=hint_result.title,
                message=hint_result.message,
                status=HintStatus.PENDING,
            )
            db.add(hint)
            db.commit()
            print(f"Created event reminder: {hint_result.title}")

    background_tasks.add_task(create_event_hint)

    return {"status": "reminder_created", "event": request.event_title}

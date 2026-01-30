from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import case
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.hint import Hint, HintStatus, HintPriority
from app.schemas.hint import HintResponse, HintStatusUpdate, PendingHintsResponse


class TimeTriggerRequest(BaseModel):
    """Request model for time-based hint triggers"""
    device_id: str
    trigger_type: str  # "same_app_duration" or "break_reminder"
    app_name: str | None = None
    window_title: str | None = None
    duration_minutes: float
    break_number: int | None = None
    context: str | None = None
    recent_windows: list[str] | None = None

router = APIRouter(prefix="/hints", tags=["hints"])


@router.get("/{device_id}/pending", response_model=PendingHintsResponse)
async def get_pending_hints(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all pending hints for a device.
    Returns hints ordered by priority (high first) and creation time.
    """
    # Use CASE statement for proper priority ordering across databases
    priority_order = case(
        (Hint.priority == HintPriority.HIGH, 1),
        (Hint.priority == HintPriority.MEDIUM, 2),
        (Hint.priority == HintPriority.LOW, 3),
        else_=4
    )

    hints = (
        db.query(Hint)
        .filter(
            Hint.device_id == device_id,
            Hint.status == HintStatus.PENDING
        )
        .order_by(
            priority_order,
            Hint.created_at.asc()
        )
        .all()
    )

    return PendingHintsResponse(
        hints=hints,
        count=len(hints)
    )


@router.patch("/{hint_id}/status", response_model=HintResponse)
async def update_hint_status(
    hint_id: int,
    status_update: HintStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the status of a hint.
    Automatically sets shown_at or dismissed_at timestamps based on status.
    """
    hint = db.query(Hint).filter(Hint.id == hint_id).first()

    if not hint:
        raise HTTPException(status_code=404, detail="Hint not found")

    # Update status
    hint.status = status_update.status

    # Set appropriate timestamps
    if status_update.status == HintStatus.SHOWN and hint.shown_at is None:
        hint.shown_at = datetime.utcnow()
    elif status_update.status == HintStatus.DISMISSED and hint.dismissed_at is None:
        hint.dismissed_at = datetime.utcnow()

    db.commit()
    db.refresh(hint)

    return hint


@router.post("/{device_id}/generate")
async def generate_hint(device_id: str, db: Session = Depends(get_db)):
    """Manually trigger hint generation for testing."""
    from app.services.hint_generator import HintGenerator
    generator = HintGenerator(db)
    hint = await generator.check_and_generate_hint(device_id)
    if hint:
        return {"status": "generated", "hint_id": hint.id}
    return {"status": "no_hint_needed"}


@router.post("/time-trigger")
async def create_time_trigger_hint(
    request: TimeTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a hint based on time-based trigger from client.

    trigger_type can be:
    - "same_app_duration": User has been in the same app for X minutes
    - "break_reminder": Time for a scheduled break
    """
    from app.services.hint_generator import HintGenerator

    print(f"⏱️ Time trigger: {request.trigger_type} | {request.app_name} | {request.duration_minutes:.1f} min")

    generator = HintGenerator(db)

    struggle_data = {
        'current_app': request.app_name,
        'window_title': request.window_title or '',
        'same_app_minutes': request.duration_minutes,
        'break_number': request.break_number,
        'session_minutes': request.duration_minutes,
        'context': request.context or '',
        'recent_windows': request.recent_windows or [],
    }

    hint = await generator.check_and_generate_hint(
        device_id=request.device_id,
        trigger_type=request.trigger_type,
        struggle_data=struggle_data
    )

    if hint:
        return {"status": "created", "hint_id": hint.id, "title": hint.title}
    return {"status": "skipped", "hint_id": None}

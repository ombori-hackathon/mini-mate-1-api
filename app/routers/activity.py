from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.activity import ActivityLog
from app.schemas.activity import ActivityBatchReport, ActivityLogResponse
from app.services.hint_generator import HintGenerator

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("/report", response_model=list[ActivityLogResponse])
async def report_activities(
    report: ActivityBatchReport,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receive activity reports and generate AI-powered hints.
    """
    created_logs = []

    for activity in report.activities:
        activity_log = ActivityLog(
            device_id=report.device_id,
            app_name=activity.app_name,
            window_title=activity.window_title,
            started_at=activity.started_at,
            ended_at=activity.ended_at,
            duration_seconds=activity.duration_seconds,
            idle_seconds=activity.idle_seconds,
            might_be_stuck=activity.might_be_stuck
        )
        db.add(activity_log)
        created_logs.append(activity_log)

    db.commit()

    for log in created_logs:
        db.refresh(log)

    # Get current activity data
    current_activity = report.activities[0] if report.activities else None
    if not current_activity:
        return created_logs

    current_app = current_activity.app_name

    # Check if this is an app switch
    prev_activity = (
        db.query(ActivityLog)
        .filter(ActivityLog.device_id == report.device_id)
        .filter(ActivityLog.id < created_logs[0].id)
        .order_by(ActivityLog.id.desc())
        .first()
    )
    is_app_switch = prev_activity and prev_activity.app_name != current_app

    # Extract context data
    struggle_data = {
        "struggle_score": current_activity.struggle_score or 0,
        "tab_switch_count": current_activity.tab_switch_count or 0,
        "back_and_forth_count": current_activity.back_and_forth_count or 0,
        "app_switch_count": current_activity.app_switch_count or 0,
        "context": current_activity.context or "",
        "recent_windows": current_activity.recent_windows or [],
        "window_title": current_activity.window_title or "",
        "current_app": current_app,
    }

    score = struggle_data["struggle_score"]
    window = struggle_data["window_title"][:50]
    switch_label = "🔄 SWITCH" if is_app_switch else "📊"
    struggle_label = "🆘 HELP!" if score >= 4 else ""
    print(f"{switch_label} {current_app} | score={score} {struggle_label} | {window}")

    # ALWAYS try to generate hints (rate limiting is in hint_generator)
    async def check_hints():
        generator = HintGenerator(db)
        await generator.check_and_generate_hint(
            report.device_id,
            is_app_switch=is_app_switch,
            struggle_data=struggle_data
        )

    background_tasks.add_task(check_hints)

    return created_logs


@router.get("/{device_id}/summary", response_model=list[ActivityLogResponse])
async def get_activity_summary(
    device_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get recent activity logs for a device."""
    activities = (
        db.query(ActivityLog)
        .filter(ActivityLog.device_id == device_id)
        .order_by(ActivityLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return activities

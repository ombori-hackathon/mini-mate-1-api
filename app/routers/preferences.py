from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user_preferences import UserPreferences
from app.schemas.preferences import UserPreferencesUpdate, UserPreferencesResponse

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/{device_id}", response_model=UserPreferencesResponse)
async def get_preferences(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user preferences for a device.
    Creates default preferences if they don't exist.
    """
    preferences = (
        db.query(UserPreferences)
        .filter(UserPreferences.device_id == device_id)
        .first()
    )

    if not preferences:
        # Create default preferences
        preferences = UserPreferences(device_id=device_id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

    return preferences


@router.patch("/{device_id}", response_model=UserPreferencesResponse)
async def update_preferences(
    device_id: str,
    updates: UserPreferencesUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user preferences for a device.
    Only updates fields that are provided in the request.
    """
    preferences = (
        db.query(UserPreferences)
        .filter(UserPreferences.device_id == device_id)
        .first()
    )

    if not preferences:
        raise HTTPException(
            status_code=404,
            detail="Preferences not found. Use GET first to create defaults."
        )

    # Update only provided fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)

    # Update timestamp
    preferences.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(preferences)

    return preferences

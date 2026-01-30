from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.activity import ActivityLog
from app.models.hint import Hint, HintStatus, HintCategory, HintPriority
from app.models.user_preferences import UserPreferences
from app.services.ai_service import ai_service
from app.config import settings


class HintGenerator:
    def __init__(self, db: Session):
        self.db = db

    async def check_and_generate_hint(
        self,
        device_id: str,
        is_app_switch: bool = False,
        struggle_data: dict = None,
        trigger_type: str = None  # "same_app_duration", "break_reminder", "session_end", or None
    ) -> Optional[Hint]:
        """Check activity patterns and generate hint if appropriate."""

        # Handle time-based triggers specially
        if trigger_type == "break_reminder":
            break_number = struggle_data.get('break_number', 1) if struggle_data else 1
            session_minutes = struggle_data.get('session_minutes', 30) if struggle_data else 30
            return await self.generate_break_reminder(device_id, break_number, session_minutes)

        if trigger_type == "session_end":
            session_minutes = struggle_data.get('session_minutes', 60) if struggle_data else 60
            return await self.generate_session_end_hint(device_id, session_minutes)

        if trigger_type == "same_app_duration":
            return await self.generate_same_app_hint(device_id, struggle_data or {})

        # 1. Get or create user preferences
        prefs = self._get_or_create_preferences(device_id)

        # 2. Check rate limits (more lenient for app switches)
        can_send = self._can_send_hint(device_id, prefs, is_app_switch=is_app_switch)
        if not can_send:
            if is_app_switch:
                print(f"⏳ Rate limited")
            return None

        # 3. Build activity summary with full context
        summary = self._build_activity_summary(device_id, is_app_switch=is_app_switch)

        # 4. Merge in struggle data from the current report
        if struggle_data:
            summary.update(struggle_data)
            score = struggle_data.get('struggle_score', 0)
            bf = struggle_data.get('back_and_forth_count', 0)
            window = struggle_data.get('window_title', '')[:40]
            if score >= 4 or bf >= 3:
                print(f"🆘 STRUGGLE: score={score}, b&f={bf}, window='{window}'")
            else:
                print(f"📊 Activity: score={score}, b&f={bf}, window='{window}'")

        # 5. Get recent hints for context
        recent_hints = self._get_recent_hints(device_id)

        # 5. Ask AI for suggestion
        suggestion = await ai_service.analyze_and_suggest_hint(
            activity_summary=summary,
            user_preferences={
                "work_session_minutes": prefs.work_session_minutes,
                "enable_break_reminders": prefs.enable_break_reminders,
                "enable_app_suggestions": prefs.enable_app_suggestions,
                "enable_workflow_tips": prefs.enable_workflow_tips,
            },
            recent_hints=recent_hints,
        )

        # 6. Create hint if suggested
        if suggestion.should_generate:
            hint = self._create_hint(device_id, suggestion)
            print(f"🎯 Generated hint: {hint.title}")
            return hint

        return None

    async def generate_break_reminder(self, device_id: str, break_number: int, session_minutes: float) -> Hint:
        """Generate a break reminder hint (deterministic, no AI needed)."""

        # Different messages based on break number
        messages = [
            ("Time for a break!", f"You've been working for {int(session_minutes)} minutes. Stand up and stretch!"),
            ("Break time!", f"Great focus! {int(session_minutes)} minutes in. Rest your eyes for a moment."),
            ("Stretch break!", f"{int(session_minutes)} minutes of work. Roll your shoulders and take a breath."),
            ("Session checkpoint!", f"Congrats on {int(session_minutes)} minutes! Take a well-deserved break."),
        ]

        idx = min(break_number - 1, len(messages) - 1)
        title, message = messages[idx]

        hint = Hint(
            device_id=device_id,
            category=HintCategory.BREAK_REMINDER,
            priority=HintPriority.HIGH,
            title=title,
            message=message,
            status=HintStatus.PENDING,
        )
        self.db.add(hint)
        self.db.commit()
        self.db.refresh(hint)

        print(f"⏰ Break reminder #{break_number}: {title}")
        return hint

    async def generate_session_end_hint(self, device_id: str, session_minutes: float) -> Hint:
        """Generate a session complete hint (deterministic, no AI needed)."""

        hours = int(session_minutes // 60)
        mins = int(session_minutes % 60)
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"

        messages = [
            ("Session Complete!", f"Amazing work! You've completed your {time_str} session. Time for a longer break!"),
            ("Great Session!", f"You did it! {time_str} of focused work. Reward yourself with a proper break."),
            ("Mission Accomplished!", f"{time_str} session done! Step away, hydrate, and recharge."),
        ]

        import random
        title, message = random.choice(messages)

        hint = Hint(
            device_id=device_id,
            category=HintCategory.BREAK_REMINDER,
            priority=HintPriority.HIGH,
            title=title,
            message=message,
            status=HintStatus.PENDING,
        )
        self.db.add(hint)
        self.db.commit()
        self.db.refresh(hint)

        print(f"🏁 Session end: {title}")
        return hint

    async def generate_same_app_hint(self, device_id: str, struggle_data: dict) -> Hint:
        """Generate a hint for extended time in the same app (deterministic)."""

        app_name = struggle_data.get('current_app', 'this app')
        window_title = struggle_data.get('window_title', '')
        duration = int(struggle_data.get('same_app_minutes', 10))

        print(f"⏱️ Same-app hint: {duration} min in {app_name}")

        # Build context string
        if window_title and window_title != app_name:
            context = f'"{window_title}" in {app_name}'
        else:
            context = app_name

        # Different messages based on duration
        if duration < 20:
            messages = [
                ("Deep Focus Mode", f"You've been in {context} for {duration} minutes. Great concentration!"),
                ("Focused Work", f"{duration} minutes on {context}. Remember to blink and breathe!"),
                ("In The Zone", f"Nice focus! {duration} min in {context}. Stay hydrated!"),
            ]
        elif duration < 40:
            messages = [
                ("Extended Focus", f"{duration} minutes in {context}. Consider a quick stretch!"),
                ("Long Session", f"You've been focused on {context} for {duration} min. Rest your eyes?"),
                ("Heads Up", f"{duration} min deep in {context}. A short break might boost productivity!"),
            ]
        else:
            messages = [
                ("Marathon Session!", f"Wow! {duration} minutes in {context}. Definitely time for a break!"),
                ("Ultra Focus", f"You've been in {context} for {duration} min! Your dedication is impressive, but please stretch!"),
                ("Time Check", f"{duration} minutes on {context}. Step away for a moment to recharge!"),
            ]

        import random
        title, message = random.choice(messages)

        hint = Hint(
            device_id=device_id,
            category=HintCategory.FOCUS_ALERT,
            priority=HintPriority.MEDIUM,
            title=title,
            message=message,
            status=HintStatus.PENDING,
        )
        self.db.add(hint)
        self.db.commit()
        self.db.refresh(hint)

        print(f"⏱️ Same-app hint: {title}")
        return hint

    def _get_or_create_preferences(self, device_id: str) -> UserPreferences:
        prefs = self.db.query(UserPreferences).filter(
            UserPreferences.device_id == device_id
        ).first()

        if not prefs:
            prefs = UserPreferences(device_id=device_id)
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)

        return prefs

    def _can_send_hint(self, device_id: str, prefs: UserPreferences, is_app_switch: bool = False) -> bool:
        """Check if we can send another hint based on rate limits."""
        now = datetime.utcnow()

        # Auto-dismiss any old pending/shown hints (cleanup)
        old_hints = self.db.query(Hint).filter(
            Hint.device_id == device_id,
            Hint.status.in_([HintStatus.PENDING, HintStatus.SHOWN]),
            Hint.created_at < now - timedelta(seconds=30)  # Older than 30 seconds
        ).all()
        for h in old_hints:
            h.status = HintStatus.DISMISSED
        if old_hints:
            self.db.commit()

        # Check minimum time since last hint created
        last_hint = self.db.query(Hint).filter(
            Hint.device_id == device_id,
        ).order_by(Hint.created_at.desc()).first()

        if last_hint:
            seconds_since_last = (now - last_hint.created_at).total_seconds()
            # Minimum 5 seconds between hints for smoother flow
            if seconds_since_last < 5:
                return False

        # Check max hints per hour limit
        one_hour_ago = now - timedelta(hours=1)
        hints_in_last_hour = self.db.query(func.count(Hint.id)).filter(
            Hint.device_id == device_id,
            Hint.created_at >= one_hour_ago
        ).scalar()

        max_hints = prefs.max_hints_per_hour if prefs.max_hints_per_hour else 10
        if hints_in_last_hour >= max_hints:
            print(f"⏳ Rate limited: {hints_in_last_hour}/{max_hints} hints this hour")
            return False

        return True

    def _build_activity_summary(self, device_id: str, is_app_switch: bool = False) -> dict:
        """Build summary of recent activity with full context."""
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        # Get activities in last hour
        activities = self.db.query(ActivityLog).filter(
            ActivityLog.device_id == device_id,
            ActivityLog.started_at >= one_hour_ago,
        ).order_by(ActivityLog.started_at.desc()).all()

        if not activities:
            return {
                "session_duration_minutes": 0,
                "dominant_app": "Unknown",
                "current_window_title": None,
                "app_switch_count": 0,
                "might_be_stuck": False,
                "idle_seconds": 0,
                "recent_apps": [],
                "is_app_switch": is_app_switch,
            }

        # Get the most recent activity for current context
        current = activities[0] if activities else None

        # Calculate session duration (time since first activity)
        first_activity = min(activities, key=lambda a: a.started_at)
        session_duration = (now - first_activity.started_at).total_seconds() / 60

        # Find dominant app
        app_durations = {}
        for activity in activities:
            duration = activity.duration_seconds or 0
            app_durations[activity.app_name] = app_durations.get(activity.app_name, 0) + duration

        dominant_app = max(app_durations, key=app_durations.get) if app_durations else "Unknown"

        # Get recent app sequence (for context)
        recent_apps = []
        seen_apps = set()
        for activity in activities[:10]:
            if activity.app_name not in seen_apps:
                recent_apps.append({
                    "app": activity.app_name,
                    "window": activity.window_title
                })
                seen_apps.add(activity.app_name)

        # Count unique app switches
        app_switch_count = 0
        prev_app = None
        for activity in reversed(activities):
            if prev_app and activity.app_name != prev_app:
                app_switch_count += 1
            prev_app = activity.app_name

        # Get the latest activity for struggle data
        latest = activities[0] if activities else None

        return {
            "session_duration_minutes": session_duration,
            "dominant_app": dominant_app,
            "current_app": current.app_name if current else "Unknown",
            "current_window_title": current.window_title if current else None,
            "app_switch_count": app_switch_count,
            "might_be_stuck": current.might_be_stuck if current else False,
            "idle_seconds": current.idle_seconds if current else 0,
            "recent_apps": recent_apps,
            "is_app_switch": is_app_switch,
            # Struggle detection fields
            "struggle_score": getattr(latest, 'struggle_score', 0) or 0 if latest else 0,
            "tab_switch_count": getattr(latest, 'tab_switch_count', 0) or 0 if latest else 0,
            "back_and_forth_count": getattr(latest, 'back_and_forth_count', 0) or 0 if latest else 0,
            "context": getattr(latest, 'context', '') or '' if latest else '',
            "recent_windows": getattr(latest, 'recent_windows', []) or [] if latest else [],
        }

    def _get_recent_hints(self, device_id: str) -> list[dict]:
        """Get recent hints for context - more hints = less repetition."""
        hints = self.db.query(Hint).filter(
            Hint.device_id == device_id,
        ).order_by(Hint.created_at.desc()).limit(10).all()

        return [
            {"category": h.category.value, "title": h.title, "message": h.message}
            for h in hints
        ]

    def _create_hint(self, device_id: str, suggestion) -> Hint:
        """Create a new hint from AI suggestion."""
        hint = Hint(
            device_id=device_id,
            category=HintCategory(suggestion.category),
            priority=HintPriority(suggestion.priority),
            title=suggestion.title,
            message=suggestion.message,
            status=HintStatus.PENDING,
        )
        self.db.add(hint)
        self.db.commit()
        self.db.refresh(hint)
        return hint

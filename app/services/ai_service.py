from typing import Optional
from pydantic import BaseModel
import os
import json
import httpx


class HintSuggestion(BaseModel):
    should_generate: bool
    category: Optional[str] = None
    priority: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    trigger_reason: Optional[str] = None


class AIService:
    """Behavior-based hints that actually help."""

    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.use_ollama = self._check_ollama()
        print(f"✅ AI ready!" if self.use_ollama else "⚠️ Ollama not available")

    def _check_ollama(self) -> bool:
        try:
            return httpx.get(f"{self.ollama_url}/api/tags", timeout=2.0).status_code == 200
        except:
            return False

    async def _call_ollama(self, prompt: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7}
                    }
                )
                if response.status_code == 200:
                    return response.json().get("response", "")
        except Exception as e:
            print(f"❌ AI error: {e}")
        return None

    async def analyze_and_suggest_hint(
        self,
        activity_summary: dict,
        user_preferences: dict,
        recent_hints: list[dict],
    ) -> HintSuggestion:
        """Analyze behavior and generate RELEVANT hints only."""

        current_app = activity_summary.get('current_app', '')
        window_title = activity_summary.get('window_title', '') or activity_summary.get('current_window_title', '') or ''
        context = activity_summary.get('context', '') or ''
        recent_windows = activity_summary.get('recent_windows', []) or []
        struggle_score = activity_summary.get('struggle_score', 0)
        back_and_forth = activity_summary.get('back_and_forth_count', 0)
        tab_switches = activity_summary.get('tab_switch_count', 0)
        app_switches = activity_summary.get('app_switch_count', 0)
        session_minutes = activity_summary.get('session_duration_minutes', 0)

        # Skip dev tools
        if current_app in ['Terminal', 'iTerm2', 'Warp', 'Activity Monitor']:
            return HintSuggestion(should_generate=False)

        # Skip Claude sessions
        if 'claude' in (window_title + context).lower():
            return HintSuggestion(should_generate=False)

        print(f"📥 Input: app={current_app}, window={window_title[:50]}, struggle={struggle_score}")

        # Detect behavior pattern
        behavior = self._detect_behavior(
            current_app=current_app,
            window_title=window_title,
            recent_windows=recent_windows,
            struggle_score=struggle_score,
            back_and_forth=back_and_forth,
            tab_switches=tab_switches,
            app_switches=app_switches,
            session_minutes=session_minutes
        )

        if not behavior:
            print(f"❌ No behavior detected")
            return HintSuggestion(should_generate=False)

        print(f"🎯 Detected: {behavior['type']} | {current_app} | {window_title[:40]}")

        # Generate hint based on detected behavior
        recent_titles = [h.get('title', '') for h in recent_hints[:5]]
        hint = await self._generate_behavior_hint(behavior, recent_titles)

        return hint

    def _detect_behavior(self, current_app: str, window_title: str, recent_windows: list,
                         struggle_score: int, back_and_forth: int, tab_switches: int,
                         app_switches: int, session_minutes: float) -> Optional[dict]:
        """Detect what the user is doing based on their behavior."""

        window_lower = window_title.lower()
        recent_lower = ' '.join(recent_windows).lower() if recent_windows else ''

        # Define app categories
        code_editors = ['Cursor', 'Code', 'Visual Studio Code', 'Xcode', 'PyCharm', 'IntelliJ IDEA', 'WebStorm', 'Sublime Text', 'Atom']
        browsers = ['Google Chrome', 'Safari', 'Arc', 'Firefox', 'Brave Browser']
        is_code_editor = current_app in code_editors
        is_browser = current_app in browsers

        # 1. DEBUGGING - User is stuck on an error (high struggle or error keywords)
        error_keywords = ['error', 'exception', 'failed', 'undefined', 'null', 'bug', 'fix', 'issue', 'problem', 'crash', 'not working']
        if struggle_score >= 4 or any(kw in window_lower or kw in recent_lower for kw in error_keywords):
            error_context = window_title
            for win in recent_windows[:3]:
                if any(kw in win.lower() for kw in error_keywords):
                    error_context = win
                    break

            return {
                'type': 'debugging',
                'error_context': error_context,
                'struggle_score': struggle_score,
                'app': current_app
            }

        # 2. CODING - In a code editor (check BEFORE research to avoid false positives)
        if is_code_editor:
            file_ext = None
            for ext in ['.py', '.js', '.ts', '.tsx', '.jsx', '.swift', '.java', '.go', '.rs', '.cpp', '.c', '.html', '.css']:
                if ext in window_title or any(ext in w for w in recent_windows):
                    file_ext = ext
                    break

            return {
                'type': 'coding',
                'app': current_app,
                'file': window_title if window_title != current_app else None,
                'file_type': file_ext,
                'recent_context': recent_windows[:3]
            }

        # 3. RESEARCHING - User is learning/searching (ONLY in browsers)
        research_keywords = ['how to', 'tutorial', 'guide', 'learn', 'documentation', 'example', 'stack overflow', 'medium', 'dev.to']
        search_in_title = 'google' in window_lower or 'search' in window_lower
        if is_browser and (search_in_title or any(kw in window_lower for kw in research_keywords)):
            search_query = window_title.split(' - ')[0] if ' - ' in window_title else window_title

            return {
                'type': 'researching',
                'query': search_query,
                'recent_searches': recent_windows[:3],
                'app': current_app
            }

        # 4. DISTRACTED - Too many app switches
        if app_switches > 10 and back_and_forth >= 2:
            return {
                'type': 'distracted',
                'app_switches': app_switches,
                'back_and_forth': back_and_forth,
                'app': current_app
            }

        # 5. BROWSING - In a browser with specific content (general browsing, not research)
        if is_browser and window_title and window_title != current_app:
            return {
                'type': 'browsing',
                'page': window_title,
                'app': current_app
            }

        # 6. COMMUNICATION - In a chat/email app
        comm_apps = ['Slack', 'Discord', 'Messages', 'Mail', 'Microsoft Teams', 'Zoom']
        if current_app in comm_apps:
            return {
                'type': 'communication',
                'app': current_app,
                'context': window_title
            }

        return None

    async def _generate_behavior_hint(self, behavior: dict, recent_hints: list) -> HintSuggestion:
        """Generate a hint specific to the detected behavior."""

        behavior_type = behavior['type']

        if behavior_type == 'debugging':
            prompt = f"""RESPOND WITH JSON ONLY. NO OTHER TEXT.

User is debugging: {behavior.get('error_context', 'unknown')}

Give a SHORT debugging tip (title: 2-4 words, message: under 15 words).

{{"title": "Check Array Init", "message": "Verify the array is defined before calling .map() on it."}}

Your response (JSON only, no explanation):"""""

        elif behavior_type == 'researching':
            prompt = f"""RESPOND WITH JSON ONLY. NO OTHER TEXT.

User searched: {behavior.get('query', 'unknown')}

Give a SHORT research tip (title: 2-4 words, message: under 15 words).

{{"title": "Try Official Docs", "message": "Check the official documentation for the most accurate information."}}

Your response (JSON only):"""""

        elif behavior_type == 'distracted':
            prompt = f"""RESPOND WITH JSON ONLY. NO OTHER TEXT.

User switched apps {behavior.get('app_switches')} times, back-and-forth {behavior.get('back_and_forth')} times.

Give a SHORT focus tip (title: 2-4 words, message: under 15 words).

{{"title": "Try Pomodoro", "message": "Set a 25-minute timer and focus on one task."}}

Your response (JSON only):"""

        elif behavior_type == 'coding':
            file_type = behavior.get('file_type', '')
            app = behavior.get('app', 'editor')

            prompt = f"""RESPOND WITH JSON ONLY. NO OTHER TEXT.

User coding in {app}, file type: {file_type or 'unknown'}.

Give a SHORT coding tip (title: 2-4 words, message: under 15 words).

{{"title": "Use Cmd+D", "message": "Select next occurrence of the word for multi-cursor editing."}}

Your response (JSON only):"""

        elif behavior_type == 'browsing':
            page = behavior.get('page', '')[:50]

            prompt = f"""RESPOND WITH JSON ONLY. NO OTHER TEXT.

User browsing: {page}

Give a SHORT relevant tip (title: 2-4 words, message: under 15 words).

{{"title": "Bookmark This", "message": "Press Cmd+D to save this page for later reference."}}

Your response (JSON only):"""

        elif behavior_type == 'communication':
            app = behavior.get('app', 'chat')

            prompt = f"""RESPOND WITH JSON ONLY. NO OTHER TEXT.

User in {app} (communication app).

Give a SHORT productivity tip (title: 2-4 words, message: under 15 words).

{{"title": "Use Threads", "message": "Reply in threads to keep conversations organized."}}

Your response (JSON only):"""

        else:
            return HintSuggestion(should_generate=False)

        response = await self._call_ollama(prompt)
        print(f"🤖 AI response: {response[:100] if response else 'None'}...")

        if response:
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    print(f"📋 JSON: {json_str}")
                    data = json.loads(json_str)
                    title = data.get("title", "")
                    message = data.get("message", "")

                    if title and message:
                        # Map behavior to valid category
                        category_map = {
                            'debugging': 'workflow_tip',
                            'researching': 'workflow_tip',
                            'distracted': 'focus_alert',
                            'coding': 'app_suggestion',
                            'browsing': 'app_suggestion',
                            'communication': 'app_suggestion',
                        }
                        category = category_map.get(behavior_type, 'workflow_tip')
                        priority = "high" if behavior_type in ['debugging', 'distracted'] else "medium"

                        print(f"✅ [{behavior_type}] {title}: {message[:40]}...")
                        return HintSuggestion(
                            should_generate=True,
                            category=category,
                            priority=priority,
                            title=title[:25],
                            message=message[:80],
                            trigger_reason=behavior_type
                        )
            except:
                pass

        return HintSuggestion(should_generate=False)

    async def generate_event_reminder(self, event_title: str) -> HintSuggestion:
        return HintSuggestion(
            should_generate=True,
            category="event_reminder",
            priority="high",
            title=f"{event_title[:18]}!",
            message=f"Time for {event_title}",
            trigger_reason="event"
        )


ai_service = AIService()

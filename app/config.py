from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/hackathon"
    debug: bool = True

    # AI Configuration
    anthropic_api_key: str = ""
    ai_model: str = "claude-3-haiku-20240307"
    ai_enabled: bool = True

    # Hint generation settings
    hint_check_interval_seconds: int = 60
    default_work_session_minutes: int = 30
    default_max_hints_per_hour: int = 3

    class Config:
        env_file = ".env"


settings = Settings()

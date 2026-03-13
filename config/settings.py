from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

from config.vocabulary import build_whisper_prompt


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""
    telegram_allowed_user_ids: list[int] = Field(default_factory=list)

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Google
    google_credentials_path: str = "data/google_tokens/credentials.json"
    google_token_path: str = "data/google_tokens/token.json"
    gmail_sender_email: str = ""
    gmail_recipient_email: str = ""

    # Calendars
    work_calendar_id: str = ""
    personal_calendar_id: str = ""

    # Google Sheets
    google_sheet_id: str = ""

    # Whisper
    whisper_model: str = "distil-large-v3"
    whisper_batch_size: int = 12
    whisper_prompt: str = Field(default_factory=build_whisper_prompt)

    # HuggingFace (for pyannote - Phase 2)
    huggingface_token: str = ""
    diarization_model: str = "pyannote/speaker-diarization-3.1"

    # Storage
    database_path: str = "data/donotes.db"
    audio_cache_dir: str = "data/audio_cache"

    # Scheduler
    morning_brief_hour: int = 8
    morning_brief_minute: int = 0
    weekly_digest_day: str = "monday"
    weekly_digest_hour: int = 9

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def abs_database_path(self) -> Path:
        return self.project_root / self.database_path

    @property
    def abs_audio_cache_dir(self) -> Path:
        return self.project_root / self.audio_cache_dir

    @property
    def abs_google_credentials_path(self) -> Path:
        return self.project_root / self.google_credentials_path

    @property
    def abs_google_token_path(self) -> Path:
        return self.project_root / self.google_token_path

    # Timezone (for Google Calendar events)
    timezone: str = "UTC"

    # User identity (for AI prompts)
    user_name: str = ""

    model_config = {"env_file": ".env", "env_prefix": "DONOTES_"}

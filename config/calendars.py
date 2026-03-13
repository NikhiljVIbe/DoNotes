from config.settings import Settings


def get_calendar_id(category: str, settings: Settings) -> str:
    """Return the Google Calendar ID for the given category."""
    if category == "personal":
        return settings.personal_calendar_id
    # work and mixed both go to work calendar
    return settings.work_calendar_id

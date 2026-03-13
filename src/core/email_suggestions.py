"""Analyze a ProcessedMessage and identify people who should receive an email."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.ai.schemas import ProcessedMessage


@dataclass
class EmailSuggestion:
    """A suggestion to email a specific person with relevant context."""

    person_name: str
    person_id: str | None = None  # populated after DB lookup
    email: str | None = None  # populated from contact book
    action_items: list[str] = field(default_factory=list)
    commitments: list[str] = field(default_factory=list)
    context: str | None = None  # general context (from people_mentioned)


# Names to exclude from suggestions (the bot owner)
try:
    from config.user_profile import SELF_NAMES
except ImportError:
    SELF_NAMES = {"me", "myself", "i"}


def build_email_suggestions(processed: ProcessedMessage) -> list[EmailSuggestion]:
    """
    Return a list of people who should potentially receive an email,
    along with the relevant action items and commitments.

    Rules:
    1. Include people who have action items assigned to them (assigned_to)
    2. Include people who have commitments made to them (made_to)
    3. Include people mentioned in the message (people_mentioned) — for social
       plans, dinner invites, meeting coordination, etc.
    - Exclude the user themselves
    - Deduplicate by normalized name
    """
    suggestions: dict[str, EmailSuggestion] = {}  # keyed by lowercase name

    # 1. People with action items assigned to them
    for item in processed.action_items:
        if item.assigned_to:
            name_lower = item.assigned_to.strip().lower()
            if name_lower in SELF_NAMES:
                continue
            if name_lower not in suggestions:
                suggestions[name_lower] = EmailSuggestion(
                    person_name=item.assigned_to.strip()
                )
            suggestions[name_lower].action_items.append(item.description)

    # 2. People with commitments made to them
    for commitment in processed.commitments:
        if commitment.made_to:
            name_lower = commitment.made_to.strip().lower()
            if name_lower in SELF_NAMES:
                continue
            if name_lower not in suggestions:
                suggestions[name_lower] = EmailSuggestion(
                    person_name=commitment.made_to.strip()
                )
            suggestions[name_lower].commitments.append(commitment.description)

    # 3. People mentioned in the message (catch social plans, meetings, etc.)
    for person in processed.people_mentioned:
        name_lower = person.name.strip().lower()
        if name_lower in SELF_NAMES:
            continue
        if name_lower not in suggestions:
            # Create a suggestion with general context from the summary
            suggestions[name_lower] = EmailSuggestion(
                person_name=person.name.strip(),
                context=processed.summary,
            )
        elif not suggestions[name_lower].context:
            # Enrich existing suggestion with context
            suggestions[name_lower].context = processed.summary

    return list(suggestions.values())

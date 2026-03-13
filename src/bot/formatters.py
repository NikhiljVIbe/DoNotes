from __future__ import annotations

from src.ai.schemas import ProcessedMessage


def format_processed_reply(processed: ProcessedMessage) -> str:
    """Format a ProcessedMessage into a plain-text Telegram reply."""
    parts: list[str] = []

    # Category & Summary
    cat = processed.category.value.upper()
    parts.append(f"[{cat}] {processed.summary}")

    # Urgency
    urgency_bar = "=" * min(processed.urgency_score, 10)
    parts.append(f"Urgency: [{urgency_bar}] {processed.urgency_score}/10")

    # Action Items
    if processed.action_items:
        parts.append("\n--- Action Items ---")
        for i, item in enumerate(processed.action_items, 1):
            line = f"  {i}. [{item.priority.value}] {item.description}"
            if item.deadline:
                line += f"\n     Deadline: {item.deadline.strftime('%b %d, %Y %I:%M %p')}"
            if item.assigned_to:
                line += f"\n     Assigned: {item.assigned_to}"
            parts.append(line)

    # Calendar Events
    if processed.calendar_events:
        parts.append("\n--- Calendar Events ---")
        for ev in processed.calendar_events:
            line = f"  - {ev.title}"
            if ev.start_time:
                line += f" ({ev.start_time.strftime('%b %d, %I:%M %p')})"
            parts.append(line)

    # Commitments
    if processed.commitments:
        parts.append("\n--- Commitments ---")
        for c in processed.commitments:
            parts.append(f"  - {c.made_by} -> {c.made_to}: {c.description}")

    # People
    if processed.people_mentioned:
        names = ", ".join(
            f"{p.name}" + (f" ({p.role})" if p.role else "")
            for p in processed.people_mentioned
        )
        parts.append(f"\nPeople: {names}")

    # Topics
    if processed.key_topics:
        topics = " | ".join(processed.key_topics)
        parts.append(f"Topics: {topics}")

    return "\n".join(parts)

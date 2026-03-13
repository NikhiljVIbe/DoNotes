from __future__ import annotations

from thefuzz import fuzz

from src.ai.schemas import ActionItem


def find_duplicates(
    new_items: list[ActionItem],
    existing_items: list[dict],
    threshold: float = 85.0,
) -> dict[int, dict]:
    """
    Check new action items against existing pending items for duplicates.
    Returns dict mapping new_item_index -> existing_item_dict for items
    above the similarity threshold.
    """
    duplicates: dict[int, dict] = {}

    for i, new_item in enumerate(new_items):
        for existing in existing_items:
            score = fuzz.token_sort_ratio(
                new_item.description, existing.get("description", "")
            )
            if score >= threshold:
                duplicates[i] = existing
                break

    return duplicates

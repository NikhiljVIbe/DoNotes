from __future__ import annotations

from src.ai.schemas import Person
from src.storage.repositories import PeopleRepo


class PeopleManager:
    """Manage the people graph from extracted conversation data."""

    def __init__(self, people_repo: PeopleRepo):
        self._repo = people_repo

    async def update_from_processed(
        self,
        people: list[Person],
        conversation_id: str,
        category: str,
    ) -> None:
        for person in people:
            person_id = await self._repo.upsert_person(
                name=person.name,
                role=person.role,
                category=category,
            )
            await self._repo.add_mention(
                person_id=person_id,
                conversation_id=conversation_id,
                context=person.context or "",
            )

from __future__ import annotations

import calendar
import json
import logging
import re
from datetime import datetime

from openai import OpenAI
from pydantic import ValidationError

from config.prompts import (
    CLASSIFY_AND_EXTRACT_SYSTEM,
    CLASSIFY_AND_EXTRACT_USER,
    CONTEXT_SECTION_TEMPLATE,
)
from src.ai.schemas import ProcessedMessage

log = logging.getLogger(__name__)


class AIClient:
    def __init__(self, api_key: str, model: str):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def process_message(
        self,
        transcript: str,
        source_type: str,
        recent_summaries: list[dict] | None = None,
        pending_items: list[dict] | None = None,
    ) -> ProcessedMessage:
        """
        Analyze a transcript using OpenAI with JSON mode.
        Returns a fully parsed ProcessedMessage.
        """
        now = datetime.now()
        system_prompt = CLASSIFY_AND_EXTRACT_SYSTEM.format(
            current_datetime=now.strftime("%Y-%m-%d %H:%M:%S (%A)")
        )

        # Build context section
        context_section = ""
        if recent_summaries or pending_items:
            summaries_text = "None" if not recent_summaries else "\n".join(
                f"- [{s.get('category', '?')}] {s.get('summary', 'N/A')} "
                f"(topics: {s.get('key_topics', '[]')})"
                for s in (recent_summaries or [])
            )
            items_text = "None" if not pending_items else "\n".join(
                f"- [{i.get('priority', 'medium')}] {i.get('description', 'N/A')} "
                f"(deadline: {i.get('deadline', 'none')})"
                for i in (pending_items or [])
            )
            context_section = CONTEXT_SECTION_TEMPLATE.format(
                recent_summaries=summaries_text,
                pending_items=items_text,
            )

        user_prompt = CLASSIFY_AND_EXTRACT_USER.format(
            context_section=context_section,
            source_type=source_type,
            transcript=transcript,
        )

        log.info("Sending to OpenAI (%s) for extraction...", self._model)

        json_schema = json.dumps(ProcessedMessage.model_json_schema(), indent=2)
        json_instruction = (
            "\n\nRespond with ONLY a valid JSON object matching this schema:\n"
            + json_schema
            + "\n\nUse ISO 8601 format for all datetime fields (e.g. 2025-03-15T10:00:00). "
            "Use null for missing optional fields."
        )

        # Newer models (gpt-5+, o-series) use max_completion_tokens
        _NEW_PARAM_MODELS = ("gpt-5", "gpt-4.5", "o1", "o3", "o4")
        if any(self._model.startswith(p) for p in _NEW_PARAM_MODELS):
            token_param = {"max_completion_tokens": 4096}
        else:
            token_param = {"max_tokens": 4096}

        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            **token_param,
            messages=[
                {"role": "system", "content": system_prompt + json_instruction},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = response.choices[0].message.content.strip()
        try:
            return ProcessedMessage.model_validate_json(raw_text)
        except ValidationError as e:
            log.warning("Validation failed, attempting date fix: %s", e)
            fixed_text = self._fix_invalid_dates(raw_text)
            return ProcessedMessage.model_validate_json(fixed_text)

    # ------------------------------------------------------------------
    @staticmethod
    def _fix_invalid_dates(raw_json: str) -> str:
        """Fix invalid dates from LLM (e.g. Feb 29 in non-leap years)."""

        _ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

        def _clamp(match: re.Match) -> str:
            ds = match.group(0)
            try:
                year, month, day = int(ds[:4]), int(ds[5:7]), int(ds[8:10])
                max_day = calendar.monthrange(year, month)[1]
                if day > max_day:
                    fixed = "{:04d}-{:02d}-{:02d}".format(year, month, max_day)
                    log.info("Fixed invalid date %s -> %s", ds, fixed)
                    return fixed
            except Exception:
                pass
            return ds

        return _ISO_RE.sub(_clamp, raw_json)

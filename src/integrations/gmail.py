from __future__ import annotations

import base64
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from googleapiclient.discovery import build
from jinja2 import Environment, FileSystemLoader

from src.ai.schemas import ProcessedMessage
from src.integrations.google_auth import GoogleAuth

log = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class GmailSender:
    def __init__(
        self,
        google_auth: GoogleAuth,
        sender_email: str,
        recipient_email: str,
    ):
        self._auth = google_auth
        self._sender = sender_email
        self._recipient = recipient_email
        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )
        self._jinja.globals["zip"] = zip

    def _get_service(self):
        creds = self._auth.get_credentials()
        return build("gmail", "v1", credentials=creds)

    def _send_html_email(self, subject: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._sender
        msg["To"] = self._recipient
        msg.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service = self._get_service()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        log.info("Email sent: %s", subject)

    def send_digest(
        self,
        processed: ProcessedMessage,
        transcript: str,
        calendar_links: list[str] | None = None,
    ) -> None:
        """Send a per-message digest email."""
        template = self._jinja.get_template("digest_email.html")
        html = template.render(
            processed=processed,
            transcript=transcript,
            calendar_links=calendar_links or [],
            now=datetime.now(),
        )

        category_emoji = {"work": "\U0001f4bc", "personal": "\U0001f3e0", "mixed": "\U0001f504"}
        emoji = category_emoji.get(processed.category.value, "\U0001f4cb")
        subject = f"{emoji} DoNotes | {processed.summary[:70]}"
        self._send_html_email(subject, html)

    def _send_html_email_to(self, to_email: str, subject: str, html_body: str) -> None:
        """Send an HTML email to a specific recipient (not the default)."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._sender
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service = self._get_service()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        log.info("Email sent to %s: %s", to_email, subject)

    def send_composed_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        category: str = "mixed",
    ) -> None:
        """Send a GPT-composed email as clean HTML to a specific recipient."""
        template = self._jinja.get_template("composed_email.html")
        html = template.render(
            subject=subject,
            body_text=body_text,
            category=category,
            now=datetime.now(),
        )
        self._send_html_email_to(to_email, subject, html)

    def send_morning_brief(
        self,
        today_events: list[dict],
        pending_items: list[dict],
        overdue_items: list[dict],
        yesterday_summaries: list[dict],
    ) -> None:
        """Send morning brief email."""
        template = self._jinja.get_template("morning_brief_email.html")
        html = template.render(
            today_events=today_events,
            pending_items=pending_items,
            overdue_items=overdue_items,
            yesterday_summaries=yesterday_summaries,
        )
        self._send_html_email("DoNotes Morning Brief", html)

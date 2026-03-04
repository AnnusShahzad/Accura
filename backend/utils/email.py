"""
Accura – Email Utilities (SMTP via aiosmtplib + Jinja2 templates)
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from config import settings

logger = logging.getLogger("accura.email")

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


async def send_email(
    to: str,
    subject: str,
    template_name: str | None = None,
    template_context: dict | None = None,
    html_body: str | None = None,
    text_body: str | None = None,
) -> None:
    """Send an email using SMTP config from settings / YAML."""

    smtp_host = settings.get("smtp.host", "localhost")
    smtp_port = settings.get("smtp.port", 587)
    smtp_user = settings.get("smtp.user", "")
    smtp_password = settings.get("smtp.password", "")
    from_name = settings.get("smtp.from_name", "Accura")
    from_email = settings.get("smtp.from_email", "noreply@accura.ai")
    use_tls = settings.get("smtp.use_tls", True)

    if template_name:
        tpl = _jinja_env.get_template(template_name)
        html_body = tpl.render(**(template_context or {}))

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to
    msg["Subject"] = subject

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user or None,
            password=smtp_password or None,
            use_tls=use_tls,
        )
        logger.info("Email sent to %s: %s", to, subject)
    except Exception:
        logger.exception("Failed to send email to %s", to)
        raise

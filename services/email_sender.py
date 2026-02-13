"""Email sending via SMTP."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config import settings
from core.logger import logger


def send_email_gmail(
    to_email: str, subject: str, html_content: str, message_id: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Send email using configured SMTP (Gmail, Zoho, etc.).

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        message_id: Optional Message-ID (if not provided, will be generated)

    Returns:
        Tuple of (success: bool, message_id: Optional[str])
    """
    if not settings.email_username or not settings.email_password:
        logger.error(
            "Email credentials not configured. Set EMAIL_USERNAME and EMAIL_PASSWORD in .env"
        )
        return False, None

    try:
        import uuid
        import socket

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_username
        msg["To"] = to_email

        if not message_id:
            domain = (
                settings.email_username.split("@")[1]
                if "@" in settings.email_username
                else socket.getfqdn()
            )
            message_id = f"<{uuid.uuid4().hex}@{domain}>"

        msg["Message-ID"] = message_id
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
                server.login(settings.email_username, settings.email_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(settings.email_username, settings.email_password)
                server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email} via SMTP with Message-ID: {message_id}")
        return True, message_id
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False, None

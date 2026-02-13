"""Simple web application for HR to review CVs and send feedback emails."""

import os
from pathlib import Path
from dotenv import load_dotenv

from flask import Flask
from config import settings
from core.logger import logger, setup_logger
from database.models import init_db
from routes import register_all_routes

load_dotenv()
setup_logger(log_level=settings.log_level)
init_db()

try:
    from database.seed_data import seed_database

    seed_database()
except Exception as e:
    logger.warning(f"Could not seed database: {str(e)}")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["ALLOWED_EXTENSIONS"] = ALLOWED_EXTENSIONS
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

if not settings.email_username or not settings.email_password:
    logger.warning(
        "Email credentials not configured. Email sending will be disabled.\n"
        "To enable email sending, add to .env file:\n"
        "  EMAIL_USERNAME=your-email@domain.com\n"
        "  EMAIL_PASSWORD=your-password\n"
        "  SMTP_HOST=smtp.zoho.eu  # or smtp.zoho.com, smtp.gmail.com\n"
        "  SMTP_PORT=587  # 587 for TLS, 465 for SSL\n"
        "  IMAP_HOST=imap.zoho.eu  # or imap.zoho.com, imap.gmail.com\n"
        "  IMAP_PORT=993  # 993 for SSL\n"
        "For Gmail: Use 'App Password' from https://myaccount.google.com/apppasswords\n"
        "For Zoho: Use your regular password or app-specific password"
    )
else:
    logger.info(
        f"Email configured for: {settings.email_username} (SMTP: {settings.smtp_host}:{settings.smtp_port}, IMAP: {settings.imap_host}:{settings.imap_port})"
    )

email_monitor = None
if (
    settings.email_monitor_enabled
    and settings.email_username
    and settings.email_password
    and settings.iod_email
    and settings.hr_email
):
    try:
        from services.email_monitor import EmailMonitor

        email_monitor = EmailMonitor(
            email_username=settings.email_username,
            email_password=settings.email_password,
            imap_host=settings.imap_host,
            imap_port=settings.imap_port,
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            iod_email=settings.iod_email,
            hr_email=settings.hr_email,
            check_interval=settings.email_check_interval,
        )
        email_monitor.start()
        logger.info(
            f"Email monitor started (IOD: {settings.iod_email}, HR: {settings.hr_email}, interval: {settings.email_check_interval}s)"
        )
    except Exception as e:
        logger.warning(f"Failed to start email monitor: {str(e)}")
elif settings.email_monitor_enabled and settings.email_username and settings.email_password:
    logger.warning(
        "Email monitoring disabled. To enable, add to .env file:\n"
        "  IOD_EMAIL=iod@company.com\n"
        "  HR_EMAIL=hr@company.com\n"
        "  EMAIL_CHECK_INTERVAL=60  # optional, default 60 seconds"
    )

register_all_routes(app)

if __name__ == "__main__":
    logger.info("Starting Flask application")
    app.run(debug=True, host="0.0.0.0", port=5000)

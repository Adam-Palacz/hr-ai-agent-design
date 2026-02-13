"""Email monitoring service that runs in background thread."""

import time
import threading
from typing import Optional
import email  # for message_from_bytes

from core.logger import logger
from services.email_listener import EmailListener
from services.email_router import EmailRouter
from agents.email_classifier_agent import EmailClassifierAgent


class EmailMonitor:
    """Background service for monitoring and processing incoming emails."""

    def __init__(
        self,
        email_username: str,
        email_password: str,
        imap_host: str,
        imap_port: int,
        smtp_host: str,
        smtp_port: int,
        smtp_use_tls: bool = True,
        iod_email: str = None,
        hr_email: str = None,
        check_interval: int = 60,
    ):
        """
        Initialize email monitor.

        Args:
            email_username: Email username
            email_password: Email password or app password
            imap_host: IMAP server hostname
            imap_port: IMAP server port
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_use_tls: Whether to use TLS for SMTP
            iod_email: Email address for IOD department
            hr_email: Email address for HR department
            check_interval: Interval between email checks in seconds (default: 60)
        """
        self.email_username = email_username
        self.email_password = email_password
        self.iod_email = iod_email
        self.hr_email = hr_email
        self.check_interval = check_interval

        self.listener = EmailListener(email_username, email_password, imap_host, imap_port)
        self.router = EmailRouter(
            email_username, email_password, smtp_host, smtp_port, smtp_use_tls, iod_email, hr_email
        )

        # Track last processed message sequence number within this process.
        # This way we react to all NEW messages (ALL),
        # regardless of whether they were already marked as read.
        self.last_msg_num: Optional[int] = None

        # Initialize AI classifier
        try:
            from config import settings

            self.classifier = EmailClassifierAgent(
                model_name=settings.openai_model, api_key=settings.api_key
            )
            logger.info(f"AI email classifier initialized with model: {settings.openai_model}")
        except Exception as e:
            logger.warning(
                f"Failed to initialize AI classifier: {str(e)}. Will use keyword-based classification."
            )
            self.classifier = None

        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start email monitoring in background thread."""
        if self.running:
            logger.warning("Email monitor is already running")
            return

        if not self.email_username or not self.email_password:
            logger.warning("Email credentials not configured. Email monitoring disabled.")
            return

        if not self.iod_email or not self.hr_email:
            logger.warning("IOD or HR email not configured. Email monitoring disabled.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Email monitor started")

    def stop(self):
        """Stop email monitoring."""
        self.running = False
        if self.listener:
            self.listener.disconnect()
        logger.info("Email monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info(f"Email monitor loop started (check interval: {self.check_interval}s)")

        while self.running:
            try:
                # Connect to email server
                if not self.listener.connect():
                    logger.debug(
                        f"Failed to connect to email server. Retrying in {self.check_interval}s."
                    )
                    time.sleep(self.check_interval)
                    continue

                # Select INBOX
                status, _ = self.listener.mail.select("INBOX")
                if status != "OK":
                    logger.warning("Failed to select INBOX for email monitoring")
                    self.listener.disconnect()
                    time.sleep(self.check_interval)
                    continue

                # Get ALL message sequence numbers
                status, data = self.listener.mail.search(None, "ALL")
                if status != "OK":
                    logger.warning(
                        f"Failed to search ALL messages in INBOX (status={status}, data={data})"
                    )
                    self.listener.disconnect()
                    time.sleep(self.check_interval)
                    continue

                raw_ids = data[0]
                if not raw_ids:
                    # No messages at all
                    self.listener.disconnect()
                    time.sleep(self.check_interval)
                    continue

                all_msg_nums = [int(x) for x in raw_ids.split()]
                if not all_msg_nums:
                    self.listener.disconnect()
                    time.sleep(self.check_interval)
                    continue

                # On first run: set last_msg_num to the latest message,
                # so we don't process the entire history.
                if self.last_msg_num is None:
                    self.last_msg_num = max(all_msg_nums)
                else:
                    # New messages have a number greater than last_msg_num
                    new_msg_nums = [n for n in all_msg_nums if n > self.last_msg_num]

                    if new_msg_nums:
                        # Track successfully processed message numbers
                        successfully_processed = []

                        for msg_num in new_msg_nums:
                            try:
                                # Fetch full message by sequence number
                                status, msg_data = self.listener.mail.fetch(
                                    str(msg_num), "(RFC822)"
                                )
                                if status != "OK" or not msg_data or msg_data[0] is None:
                                    logger.warning(
                                        f"Failed to fetch email seq={msg_num} (status={status})"
                                    )
                                    continue

                                email_body = msg_data[0][1]
                                email_message = email.message_from_bytes(email_body)

                                # Parse using listener helper
                                email_data = self.listener._parse_email(email_message)
                                if not email_data:
                                    logger.warning(f"Parsed email seq={msg_num} returned None")
                                    continue

                                email_data["uid"] = str(msg_num)

                                # Classify email using AI agent
                                classification = self.listener.classify_email(
                                    email_data, classifier_agent=self.classifier
                                )
                                logger.info(
                                    f"Email seq={msg_num} from {email_data.get('from_email')} "
                                    f"classified as: {classification}"
                                )

                                # Route email
                                success = self.router.route_email(email_data, classification)

                                if success:
                                    logger.info(f"Email seq={msg_num} processed successfully")
                                    # Only track successfully processed messages
                                    successfully_processed.append(msg_num)
                                else:
                                    logger.warning(
                                        f"Failed to route email seq={msg_num} from {email_data.get('from_email')}"
                                    )
                                    # Don't add to successfully_processed - will retry next cycle

                            except Exception as e:
                                logger.error(
                                    f"Error processing email seq={msg_num}: {str(e)}", exc_info=True
                                )
                                # Don't add to successfully_processed - will retry next cycle

                        # Advance to highest successfully processed (failed messages are not retried to avoid duplicate processing)
                        if successfully_processed:
                            self.last_msg_num = max(successfully_processed)
                            logger.debug(
                                f"Updated last_msg_num to {self.last_msg_num} ({len(successfully_processed)} messages processed)"
                            )

                # Disconnect
                self.listener.disconnect()

                # Wait before next check
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in email monitor loop: {str(e)}", exc_info=True)
                time.sleep(self.check_interval)

"""Email listener service for monitoring incoming Gmail messages."""

import imaplib
import email
import email.header
import re
from typing import Optional, Dict, List
from datetime import datetime
from email.message import Message
from email.utils import parsedate_to_datetime

from core.logger import logger


class EmailListener:
    """Service for listening to incoming Gmail emails."""

    # Keywords for IOD/RODO classification
    IOD_KEYWORDS = [
        "rodo",
        "iod",
        "dpo",
        "gdpr",
        "dane osobowe",
        "ochrona danych",
        "sprzeciw",
        "zgoda",
        "wycofanie",
        "skarga",
        "uodo",
        "organ nadzorczy",
        "profilowanie",
        "automatyczna decyzja",
        "sztuczna inteligencja",
        "ai",
        "si",
    ]

    # Keywords for consent classification
    CONSENT_KEYWORDS_POSITIVE = [
        "zgoda",
        "zgadzam się",
        "wyrażam zgodę",
        "tak",
        "chcę",
        "zainteresowany",
        "rozważenie",
        "inne oferty",
        "inne stanowiska",
        "inne pozycje",
        "inne rekrutacje",
    ]

    CONSENT_KEYWORDS_NEGATIVE = [
        "nie zgadzam się",
        "odmawiam",
        "nie",
        "nie chcę",
        "nie wyrażam zgody",
        "wycofuję zgodę",
        "nie jestem zainteresowany",
        "nie rozważaj",
    ]

    def __init__(
        self,
        email_username: str,
        email_password: str,
        imap_server: str = "imap.zoho.com",
        imap_port: int = 993,
    ):
        """
        Initialize email listener.

        Args:
            email_username: Email username/address
            email_password: Email password or app password
            imap_server: IMAP server address (default: imap.zoho.com)
            imap_port: IMAP server port (default: 993 for SSL)
        """
        self.email_username = email_username
        self.email_password = email_password
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.mail = None

    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            if not self.email_username or not self.email_password:
                logger.error("Email credentials not provided to EmailListener")
                return False

            # Create IMAP connection with timeout (only this socket, not global default)
            import socket

            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port, timeout=30)
            self.mail.login(self.email_username, self.email_password)
            logger.debug(f"Connected to IMAP server {self.imap_server}: {self.email_username}")
            return True
        except socket.timeout:
            logger.error(
                f"IMAP connection timeout to {self.imap_server}:{self.imap_port}. Check network/firewall."
            )
            return False
        except socket.error as e:
            error_msg = str(e)
            if "EOF" in error_msg or "Connection reset" in error_msg:
                logger.warning(
                    f"IMAP connection error (EOF/reset) to {self.imap_server}:{self.imap_port}. "
                    "This may be temporary. Will retry in next cycle. "
                    "Possible causes: server-side connection limit, firewall, or network issue."
                )
            else:
                logger.error(
                    f"IMAP socket error to {self.imap_server}:{self.imap_port}: {error_msg}"
                )
            return False
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "AUTHENTICATIONFAILED" in error_msg or "Invalid credentials" in error_msg:
                logger.error(
                    f"IMAP authentication failed for {self.email_username} on {self.imap_server}. "
                    "This usually means:\n"
                    "  1. Wrong username or password\n"
                    "  2. For Gmail: You need 'App Password' instead of regular password\n"
                    "  3. For Zoho: Check if password is correct and account is active\n"
                    "  4. IMAP might be disabled in your email account settings"
                )
            else:
                logger.error(f"IMAP protocol error to {self.imap_server}: {error_msg}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to connect to IMAP server {self.imap_server}:{self.imap_port}: {str(e)}"
            )
            return False

    def disconnect(self):
        """Disconnect from Gmail IMAP server."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                # logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.warning(f"Error disconnecting from IMAP: {str(e)}")
            finally:
                self.mail = None

    def get_unread_emails(self, folder: str = "INBOX") -> List[Dict]:
        """
        Get unread emails from specified folder.

        Args:
            folder: Email folder to check (default: 'INBOX')

        Returns:
            List of email dictionaries with keys: id, from_email, subject, body, date, message_id, in_reply_to
        """
        if not self.mail:
            if not self.connect():
                return []

        try:
            # Select folder
            status, messages = self.mail.select(folder)
            if status != "OK":
                logger.error(
                    f"Failed to select folder {folder} (status={status}, messages={messages})"
                )
                return []

            # Search for unread emails
            status, message_numbers = self.mail.search(None, "UNSEEN")
            if status != "OK":
                logger.error(
                    f"Failed to search for unread emails (status={status}, data={message_numbers})"
                )
                return []

            raw_ids = message_numbers[0]
            if not raw_ids:
                # No unread emails
                return []

            message_ids = raw_ids.split()

            email_list = []

            for msg_num in message_ids:
                try:
                    # Fetch email
                    status, msg_data = self.mail.fetch(msg_num, "(RFC822)")
                    if status != "OK" or not msg_data or msg_data[0] is None:
                        logger.warning(f"Failed to fetch email {msg_num} (status={status})")
                        continue

                    # Parse email
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)

                    # Extract email data
                    email_data = self._parse_email(email_message)
                    if email_data:
                        email_data["uid"] = msg_num.decode()
                        email_list.append(email_data)
                    else:
                        logger.warning(f"Parsed email {msg_num} returned None")

                except Exception as e:
                    logger.warning(f"Error parsing email {msg_num}: {str(e)}", exc_info=True)
                    continue

            logger.info(f"Found {len(email_list)} unread emails in {folder} after parsing")
            return email_list

        except Exception as e:
            logger.error(f"Error getting unread emails: {str(e)}")
            return []

    def _parse_email(self, email_message: Message) -> Optional[Dict]:
        """Parse email message into dictionary."""
        try:
            # Get headers
            subject = self._decode_header(email_message.get("Subject", ""))
            from_email = self._decode_header(email_message.get("From", ""))
            message_id = email_message.get("Message-ID", "")
            in_reply_to = email_message.get("In-Reply-To", "")
            date_str = email_message.get("Date", "")

            # Parse date
            try:
                date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except Exception:
                date = datetime.now()

            # Extract email address from From field
            from_email_clean = self._extract_email_address(from_email)

            # Get email body
            body = self._get_email_body(email_message)

            return {
                "from_email": from_email_clean,
                "from_name": from_email,
                "subject": subject,
                "body": body,
                "date": date,
                "message_id": message_id,
                "in_reply_to": in_reply_to,
                "raw_message": email_message,
            }
        except Exception as e:
            logger.error(f"Error parsing email: {str(e)}")
            return None

    def _decode_header(self, header: str) -> str:
        """Decode email header (handles problematic encodings like 'unknown-8bit')."""
        try:
            decoded_parts = email.header.decode_header(header)
            decoded_string = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    # Try declared encoding first, fall back to utf-8 on errors or unknown encodings
                    if encoding:
                        try:
                            decoded_string += part.decode(encoding, errors="ignore")
                        except (LookupError, UnicodeError):
                            # Unknown codec (e.g. 'unknown-8bit') or decode error – fall back to utf-8
                            decoded_string += part.decode("utf-8", errors="ignore")
                    else:
                        decoded_string += part.decode("utf-8", errors="ignore")
                else:
                    decoded_string += part
            return decoded_string
        except Exception as e:
            logger.warning(f"Error decoding header: {str(e)}")
            return str(header)

    def _extract_email_address(self, email_string: str) -> str:
        """Extract email address from 'Name <email@domain.com>' format."""
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", email_string)
        if match:
            return match.group(0)
        return email_string

    def _get_email_body(self, email_message: Message) -> str:
        """Extract email body text."""
        body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                # Get text content
                if content_type == "text/plain":
                    try:
                        body_bytes = part.get_payload(decode=True)
                        if body_bytes:
                            charset = part.get_content_charset() or "utf-8"
                            body += body_bytes.decode(charset, errors="ignore")
                    except Exception as e:
                        logger.warning(f"Error decoding email body part: {str(e)}")
                elif content_type == "text/html":
                    # Fallback to HTML if no plain text
                    if not body:
                        try:
                            body_bytes = part.get_payload(decode=True)
                            if body_bytes:
                                charset = part.get_content_charset() or "utf-8"
                                html_body = body_bytes.decode(charset, errors="ignore")
                                # Simple HTML to text conversion (remove tags)
                                body = re.sub(r"<[^>]+>", "", html_body)
                        except Exception as e:
                            logger.warning(f"Error decoding HTML body: {str(e)}")
        else:
            # Not multipart
            try:
                body_bytes = email_message.get_payload(decode=True)
                if body_bytes:
                    charset = email_message.get_content_charset() or "utf-8"
                    body = body_bytes.decode(charset, errors="ignore")
            except Exception as e:
                logger.warning(f"Error decoding email body: {str(e)}")

        return body.strip()

    def mark_as_read(self, uid: str, folder: str = "INBOX") -> bool:
        """Mark email as read."""
        if not self.mail:
            return False

        try:
            self.mail.select(folder)
            self.mail.store(uid, "+FLAGS", "\\Seen")
            return True
        except Exception as e:
            logger.error(f"Error marking email as read: {str(e)}")
            return False

    def classify_email(self, email_data: Dict, classifier_agent=None) -> str:
        """
        Classify email into categories using AI agent.

        Args:
            email_data: Email dictionary with 'subject' and 'body' keys
            classifier_agent: Optional EmailClassifierAgent instance (if None, uses simple keyword matching)

        Returns:
            Classification: 'iod', 'consent_yes', 'consent_no', or 'default'
        """
        # If AI classifier is available, use it
        if classifier_agent:
            try:
                classification = classifier_agent.classify_email(
                    from_email=email_data.get("from_email", ""),
                    subject=email_data.get("subject", ""),
                    body=email_data.get("body", ""),
                )
                logger.info(
                    f"Email classified by AI as '{classification.category}' "
                    f"(confidence: {classification.confidence:.2f})"
                )
                return classification.category
            except Exception as e:
                logger.warning(
                    f"AI classification failed, falling back to keyword matching: {str(e)}"
                )

        # Fallback to simple keyword matching
        text = f"{email_data.get('subject', '')} {email_data.get('body', '')}".lower()

        # Check for IOD keywords (at least 1 critical one required)
        critical_iod_keywords = [
            "rodo",
            "iod",
            "dpo",
            "gdpr",
            "dane osobowe",
            "ochrona danych",
            "uodo",
            "organ nadzorczy",
            "profilowanie",
            "automatyczna decyzja",
        ]
        found_iod_keywords = [kw for kw in critical_iod_keywords if kw.lower() in text]

        if len(found_iod_keywords) >= 1:
            logger.info(f"Email classified as IOD (keywords: {found_iod_keywords})")
            return "iod"

        # Check for consent keywords
        for keyword in self.CONSENT_KEYWORDS_POSITIVE:
            if keyword.lower() in text:
                logger.info(f"Email classified as consent_yes (keyword: {keyword})")
                return "consent_yes"

        for keyword in self.CONSENT_KEYWORDS_NEGATIVE:
            if keyword.lower() in text:
                logger.info(f"Email classified as consent_no (keyword: {keyword})")
                return "consent_no"

        # Default classification
        logger.info("Email classified as default (HR)")
        return "default"

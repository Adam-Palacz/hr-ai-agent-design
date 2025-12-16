"""Email router service for handling classified emails."""
import smtplib
from typing import Optional, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from core.logger import logger
from database.models import (
    get_feedback_email_by_message_id,
    get_candidate_by_email,
    get_candidate_by_id,
    update_candidate
)


class EmailRouter:
    """Service for routing classified emails to appropriate departments."""
    
    def __init__(
        self,
        email_username: str,
        email_password: str,
        smtp_host: str,
        smtp_port: int,
        smtp_use_tls: bool = True,
        iod_email: str = None,
        hr_email: str = None
    ):
        """
        Initialize email router.
        
        Args:
            email_username: Email username for sending emails
            email_password: Email password or app password
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_use_tls: Whether to use TLS (True for port 587, False for port 465)
            iod_email: Email address for IOD department
            hr_email: Email address for HR department
        """
        self.email_username = email_username
        self.email_password = email_password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_use_tls = smtp_use_tls
        self.iod_email = iod_email
        self.hr_email = hr_email
        # Track processed emails to prevent duplicates (using Message-ID or UID)
        self.processed_emails = set()
    
    def route_email(self, email_data: Dict, classification: str) -> bool:
        """
        Route email based on classification.
        
        Args:
            email_data: Email dictionary
            classification: Email classification ('iod', 'consent_yes', 'consent_no', 'default')
            
        Returns:
            True if routing was successful
        """
        try:
            # Check for duplicates using Message-ID or UID
            email_id = email_data.get('message_id') or email_data.get('uid')
            if email_id:
                if email_id in self.processed_emails:
                    logger.warning(f"Email {email_id} already processed, skipping duplicate")
                    return True  # Return True to avoid reprocessing
                self.processed_emails.add(email_id)
                # Keep only last 1000 processed emails to prevent memory issues
                if len(self.processed_emails) > 1000:
                    # Remove oldest entries (simple approach: clear and rebuild from recent)
                    self.processed_emails = set(list(self.processed_emails)[-500:])
            
            if classification == 'iod':
                return self._route_to_iod(email_data)
            elif classification in ['consent_yes', 'consent_no']:
                return self._handle_consent(email_data, classification)
            else:  # default
                return self._route_to_hr(email_data)
        except Exception as e:
            logger.error(f"Error routing email: {str(e)}", exc_info=True)
            return False
    
    def _route_to_iod(self, email_data: Dict) -> bool:
        """Route email to IOD department, create ticket, and send acknowledgment to sender."""
        try:
            from datetime import datetime, timedelta
            from database.models import (
                create_ticket, TicketDepartment, TicketPriority, TicketStatus,
                get_candidate_by_email
            )
            
            # Create ticket for IOD
            from_email = email_data.get('from_email', 'Nieznany')
            email_subject = email_data.get('subject', 'Brak tematu')
            email_body = email_data.get('body', 'Brak treści')
            
            # Try to find related candidate (get the latest one if multiple exist)
            related_candidate_id = None
            try:
                from database.models import get_all_candidates
                # Get all candidates with this email and take the latest one (most recent created_at or highest ID)
                all_candidates = get_all_candidates()
                candidates_with_email = [c for c in all_candidates if c.email.lower() == from_email.lower()]
                if candidates_with_email:
                    # Sort by created_at DESC (most recent first), then by ID DESC as fallback
                    # Use a tuple for sorting: (created_at timestamp, id) - both descending
                    latest_candidate = max(
                        candidates_with_email, 
                        key=lambda c: (
                            c.created_at.timestamp() if c.created_at else 0,
                            c.id or 0
                        )
                    )
                    related_candidate_id = latest_candidate.id
                    logger.info(f"Found candidate {related_candidate_id} ({latest_candidate.full_name}) for email {from_email} (selected latest from {len(candidates_with_email)} candidates)")
            except Exception as e:
                logger.warning(f"Error finding candidate for email {from_email}: {str(e)}")
                pass
            
            # Create ticket with 7 days deadline for IOD incidents
            deadline = datetime.now() + timedelta(days=7)
            ticket_description = (
                f"Email od: {from_email}\n"
                f"Temat: {email_subject}\n\n"
                f"Treść wiadomości:\n{email_body}\n\n"
                f"Message-ID: {email_data.get('message_id', 'Brak')}"
            )
            
            try:
                ticket = create_ticket(
                    department=TicketDepartment.IOD,
                    priority=TicketPriority.HIGH,
                    description=ticket_description,
                    deadline=deadline,
                    related_candidate_id=related_candidate_id,
                    related_email_id=email_data.get('message_id')
                )
                logger.info(f"Created ticket #{ticket.id} for IOD incident from {from_email}")
            except Exception as e:
                logger.warning(f"Failed to create ticket for IOD: {str(e)}")
            
            # Forward email to IOD
            subject = f"[IOD] {email_subject}"
            body = f"""
Email otrzymany od: {from_email}
Data: {email_data.get('date', 'Nieznana')}
Temat: {email_subject}

---
Treść wiadomości:
---

{email_body}

---
Oryginalny Message-ID: {email_data.get('message_id', 'Brak')}
In-Reply-To: {email_data.get('in_reply_to', 'Brak')}
"""
            
            success = self._send_email(
                to_email=self.iod_email,
                subject=subject,
                body=body,
                reply_to=from_email
            )
            
            if success:
                # Send acknowledgment to original sender
                ack_subject = "Re: " + email_subject
                ack_body = """
Dziękujemy za kontakt.

Twoja wiadomość została przekazana do działu Inspektora Ochrony Danych (IOD) w celu rozpatrzenia.

Otrzymasz odpowiedź w najkrótszym możliwym terminie.

Z wyrazami szacunku

Dział HR
"""
                self._send_email(
                    to_email=from_email,
                    subject=ack_subject,
                    body=ack_body
                )
                logger.info(f"Email routed to IOD and acknowledgment sent to {from_email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error routing email to IOD: {str(e)}", exc_info=True)
            return False
    
    def _handle_consent(self, email_data: Dict, classification: str) -> bool:
        """Handle consent email and update database."""
        try:
            from_email = email_data.get('from_email', '')
            if not from_email:
                logger.warning("Cannot handle consent - no email address")
                return False

            # 1) Spróbuj powiązać kandydata po Message-ID (odpowiedź na nasz feedback)
            candidate = None
            in_reply_to = email_data.get('in_reply_to') or email_data.get('message_id')
            feedback_email = None

            if in_reply_to:
                # Normalizuj Message-ID (zostaw tak, jak zapisaliśmy w bazie, zwykle z <>)
                possible_ids = {in_reply_to.strip()}
                # Czasem klient usuwa nawiasy <> – spróbuj też bez nich
                if in_reply_to.startswith("<") and in_reply_to.endswith(">"):
                    possible_ids.add(in_reply_to[1:-1].strip())

                for mid in possible_ids:
                    try:
                        feedback_email = get_feedback_email_by_message_id(mid)
                        if feedback_email:
                            break
                    except Exception as e:
                        logger.warning(f"Error looking up feedback_email by Message-ID={mid}: {e}")

            if feedback_email:
                # Mamy powiązany feedback → znajdź kandydata po candidate_id
                try:
                    candidate = get_candidate_by_id(feedback_email.candidate_id)
                    if candidate:
                        logger.info(
                            f"Consent email linked to candidate {candidate.id} via Message-ID "
                            f"({feedback_email.message_id})"
                        )
                except Exception as e:
                    logger.warning(f"Error loading candidate by id {feedback_email.candidate_id}: {e}")

            # 2) Jeśli nie udało się po Message-ID, spróbuj po adresie email
            if not candidate:
                candidate = get_candidate_by_email(from_email)

            if not candidate:
                logger.warning(
                    f"Cannot find candidate for consent handling. "
                    f"from_email={from_email}, in_reply_to={in_reply_to}"
                )
                # Still route to HR for manual handling
                return self._route_to_hr(email_data)
            
            # Update consent in database
            consent_value = classification == 'consent_yes'
            update_candidate(
                candidate.id,
                consent_for_other_positions=consent_value
            )
            
            logger.info(f"Updated consent_for_other_positions for candidate {candidate.id} ({from_email}) to {consent_value}")
            
            # Send acknowledgment
            ack_subject = "Re: " + email_data.get('subject', 'Twoja wiadomość')
            if consent_value:
                ack_body = """
Dziękujemy za kontakt.

Zarejestrowaliśmy Twoją zgodę na rozważenie Twojej kandydatury w kontekście innych stanowisk.

Jeśli znajdziemy odpowiednią dla Ciebie ofertę, skontaktujemy się z Tobą niezwłocznie.

Jeśli chciałbyś zmienić zdanie, prosimy o poinformowanie nas o tym, odpowiadając na tego maila.

Z wyrazami szacunku

Dział HR
"""
            else:
                ack_body = """
Dziękujemy za kontakt.

Zarejestrowaliśmy informację, że nie wyrażasz zgody na rozważenie Twojej kandydatury w kontekście innych stanowisk.

Jeśli chciałbyś zmienić zdanie, prosimy o poinformowanie nas o tym, odpowiadając na tego maila.

Z wyrazami szacunku

Dział HR
"""
            
            self._send_email(
                to_email=from_email,
                subject=ack_subject,
                body=ack_body
            )

            # Inform HR o zmianie zgody (pełniejszy obraz sytuacji)
            try:
                hr_subject = f"[HR] Zmiana zgody kandydata na inne rekrutacje – {candidate.first_name} {candidate.last_name}"
                hr_body = f"""
Kandydat: {candidate.first_name} {candidate.last_name}
Email: {candidate.email}
ID kandydata w systemie: {candidate.id}

Nowa wartość zgody na inne stanowiska: {"TAK" if consent_value else "NIE"}

Oryginalna wiadomość kandydata:
--------------------------------
Temat: {email_data.get('subject', 'Brak tematu')}

{email_data.get('body', 'Brak treści')}
"""
                self._send_email(
                    to_email=self.hr_email,
                    subject=hr_subject,
                    body=hr_body
                )
                logger.info(f"HR notified about consent change for candidate {candidate.id}")
            except Exception as e:
                logger.warning(f"Failed to notify HR about consent change: {e}")
            
            logger.info(f"Consent handled and acknowledgment sent to {from_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling consent: {str(e)}", exc_info=True)
            return False
    
    def _route_to_hr(self, email_data: Dict) -> bool:
        """Route email to HR department."""
        try:
            subject = f"[HR] {email_data.get('subject', 'Brak tematu')}"
            body = f"""
Email otrzymany od: {email_data.get('from_email', 'Nieznany')}
Data: {email_data.get('date', 'Nieznana')}
Temat: {email_data.get('subject', 'Brak tematu')}

---
Treść wiadomości:
---

{email_data.get('body', 'Brak treści')}

---
Oryginalny Message-ID: {email_data.get('message_id', 'Brak')}
In-Reply-To: {email_data.get('in_reply_to', 'Brak')}
"""
            
            success = self._send_email(
                to_email=self.hr_email,
                subject=subject,
                body=body,
                reply_to=email_data.get('from_email')
            )
            
            if success:
                logger.info(f"Email routed to HR: {email_data.get('from_email')}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error routing email to HR: {str(e)}", exc_info=True)
            return False
    
    def _send_email(self, to_email: str, subject: str, body: str, reply_to: Optional[str] = None) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_username
            msg['To'] = to_email
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Add text content
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Send email via SMTP
            if self.smtp_port == 465:
                # Use SSL for port 465
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.email_username, self.email_password)
                    server.send_message(msg)
            else:
                # Use TLS for port 587
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.smtp_use_tls:
                        server.starttls()
                    server.login(self.email_username, self.email_password)
                    server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False


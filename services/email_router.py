"""Email router service for handling classified emails."""

import smtplib
import os
from typing import Optional, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.logger import logger
from config.settings import settings
from database.models import (
    get_feedback_email_by_message_id,
    get_candidate_by_email,
    get_candidate_by_id,
    update_candidate,
)
from agents.query_classifier_agent import QueryClassifierAgent
from agents.query_responder_agent import QueryResponderAgent
from agents.rag_response_validator_agent import RAGResponseValidatorAgent
from services.qdrant_service import QdrantRAG


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
        hr_email: str = None,
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
        # Use insertion-ordered dict to preserve recency when trimming
        self.processed_emails: dict[str, None] = {}
        self.max_processed_emails = 1000  # Maximum number of processed emails to track

        # Initialize AI client for ticket priority/deadline determination
        try:
            from openai import AzureOpenAI

            self.ai_client = AzureOpenAI(
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.api_key,
            )
            self.model_name = settings.openai_model
            logger.info("AI client initialized for ticket priority/deadline determination")
        except Exception as e:
            logger.warning(
                f"Failed to initialize AI client: {e}. Will use default priority/deadline."
            )
            self.ai_client = None
            self.model_name = None

        # Initialize AI agents for query handling
        try:
            self.query_classifier = QueryClassifierAgent(model_name=settings.openai_model)
            self.query_responder = QueryResponderAgent(model_name=settings.openai_model)
            self.rag_validator = RAGResponseValidatorAgent(model_name=settings.openai_model)
            # Initialize RAG (will be lazy-loaded when needed)
            self.rag_db = None
            logger.info("Query classification agents initialized")
        except Exception as e:
            logger.warning(
                f"Failed to initialize query agents: {e}. Will forward all queries to HR."
            )
            self.query_classifier = None
            self.query_responder = None
            self.rag_validator = None
            self.rag_db = None

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
            # Check for duplicates using Message-ID or UID (normalize to string)
            # Use combination of UID and Message-ID for better deduplication
            uid = str(email_data.get("uid", ""))
            message_id = str(email_data.get("message_id", ""))

            # Create unique identifier: prefer Message-ID, fallback to UID, or combination
            if message_id and message_id != "":
                email_id = message_id
            elif uid and uid != "":
                email_id = f"uid:{uid}"
            else:
                # Fallback: use from_email + subject + date as identifier
                email_id = f"{email_data.get('from_email', 'unknown')}:{email_data.get('subject', 'no-subject')}:{email_data.get('date', 'no-date')}"

            if email_id:
                if email_id in self.processed_emails:
                    logger.warning(
                        f"Email {email_id} already processed (classification: {classification}, "
                        f"from: {email_data.get('from_email', 'unknown')}), skipping duplicate"
                    )
                    return True  # Return True to avoid reprocessing
                self.processed_emails[email_id] = None
                logger.debug(
                    f"Marking email {email_id} as processed (classification: {classification})"
                )
                # Keep only last N processed emails (oldest evicted first)
                if len(self.processed_emails) > self.max_processed_emails:
                    keep_count = self.max_processed_emails // 2
                    keys = list(self.processed_emails)
                    for k in keys[:-keep_count]:
                        del self.processed_emails[k]
                    logger.debug(
                        f"Trimmed processed_emails to {len(self.processed_emails)} entries"
                    )

            if classification == "iod":
                return self._route_to_iod(email_data)
            elif classification in ["consent_yes", "consent_no"]:
                return self._handle_consent(email_data, classification)
            else:  # default - general query
                return self._handle_general_query(email_data)
        except Exception as e:
            logger.error(f"Error routing email: {str(e)}", exc_info=True)
            return False

    def _route_to_iod(self, email_data: Dict) -> bool:
        """Route email to IOD department, create ticket, and send acknowledgment to sender."""
        try:
            from datetime import datetime, timedelta
            from database.models import (
                create_ticket,
                TicketDepartment,
                TicketPriority,
            )

            # Create ticket for IOD
            from_email = email_data.get("from_email", "Nieznany")
            email_subject = email_data.get("subject", "Brak tematu")
            email_body = email_data.get("body", "Brak treści")

            # Try to find related candidate (get the latest one if multiple exist)
            related_candidate_id = None
            try:
                from database.models import get_all_candidates

                # Get all candidates with this email and take the latest one (most recent created_at or highest ID)
                all_candidates = get_all_candidates()
                candidates_with_email = [
                    c for c in all_candidates if c.email.lower() == from_email.lower()
                ]
                if candidates_with_email:
                    # Sort by created_at DESC (most recent first), then by ID DESC as fallback
                    # Use a tuple for sorting: (created_at timestamp, id) - both descending
                    latest_candidate = max(
                        candidates_with_email,
                        key=lambda c: (c.created_at.timestamp() if c.created_at else 0, c.id or 0),
                    )
                    related_candidate_id = latest_candidate.id
                    logger.info(
                        f"Found candidate {related_candidate_id} ({latest_candidate.full_name}) for email {from_email} (selected latest from {len(candidates_with_email)} candidates)"
                    )
            except Exception as e:
                logger.warning(f"Error finding candidate for email {from_email}: {str(e)}")
                pass

            # Check if ticket already exists for this email (prevent duplicates)
            message_id = email_data.get("message_id")
            existing_ticket = None
            if message_id:
                try:
                    from database.models import get_all_tickets

                    all_tickets = get_all_tickets()
                    # Check if ticket with same related_email_id already exists
                    existing_ticket = next(
                        (t for t in all_tickets if t.related_email_id == message_id), None
                    )
                    if existing_ticket:
                        logger.info(
                            f"Ticket #{existing_ticket.id} already exists for email {message_id}, skipping duplicate ticket creation"
                        )
                except Exception as e:
                    logger.warning(f"Error checking for existing ticket: {str(e)}")

            # Create ticket only if it doesn't exist
            if not existing_ticket:
                deadline = datetime.now() + timedelta(days=7)
                ticket_description = (
                    f"Email od: {from_email}\n"
                    f"Temat: {email_subject}\n\n"
                    f"Treść wiadomości:\n{email_body}\n\n"
                    f"Message-ID: {message_id or 'Brak'}"
                )

                try:
                    ticket = create_ticket(
                        department=TicketDepartment.IOD,
                        priority=TicketPriority.HIGH,
                        description=ticket_description,
                        deadline=deadline,
                        related_candidate_id=related_candidate_id,
                        related_email_id=message_id,
                    )
                    logger.info(f"Created ticket #{ticket.id} for IOD incident from {from_email}")
                except Exception as e:
                    logger.warning(f"Failed to create ticket for IOD: {str(e)}")

            # Check if acknowledgment was already sent (by checking if ticket exists)
            # If ticket exists, it means this email was already processed
            if existing_ticket:
                logger.info(
                    f"Email {message_id or 'with UID'} already processed (ticket #{existing_ticket.id} exists), skipping duplicate processing"
                )
                return True  # Return True to avoid reprocessing

            # Forward email to IOD
            subject = f"[IOD] {email_subject}"
            # Ensure body is not empty - if email_body is empty, add default message
            if not email_body or not email_body.strip():
                email_body = "(Brak treści w oryginalnej wiadomości)"
                logger.warning(f"Empty email body from {from_email}, using default message")

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
                to_email=self.iod_email, subject=subject, body=body, reply_to=from_email
            )

            # Send acknowledgment to original sender (always, even if forwarding to IOD failed)
            # Ticket was created, so candidate should be notified
            ack_subject = "Re: " + email_subject
            ack_body = """
Dziękujemy za kontakt.

Twoja wiadomość została przekazana do działu Inspektora Ochrony Danych (IOD) w celu rozpatrzenia.

Otrzymasz odpowiedź w najkrótszym możliwym terminie.

Z wyrazami szacunku

Dział HR
"""
            ack_success = self._send_email(to_email=from_email, subject=ack_subject, body=ack_body)

            if success:
                if ack_success:
                    logger.info(f"Email routed to IOD and acknowledgment sent to {from_email}")
                else:
                    logger.warning(
                        f"Email routed to IOD, but failed to send acknowledgment to {from_email}"
                    )
            else:
                if ack_success:
                    logger.warning(
                        f"Failed to send email to IOD for {from_email}, but acknowledgment sent to candidate"
                    )
                else:
                    logger.error(f"Failed to send email to IOD and acknowledgment to {from_email}")

            # Return True if either forwarding or acknowledgment succeeded (ticket was created)
            return success or ack_success

        except Exception as e:
            logger.error(f"Error routing email to IOD: {str(e)}", exc_info=True)
            return False

    def _handle_consent(self, email_data: Dict, classification: str) -> bool:
        """Handle consent email and update database."""
        try:
            from_email = email_data.get("from_email", "")
            if not from_email:
                logger.warning("Cannot handle consent - no email address")
                return False

            # 1) Try to link candidate by Message-ID (reply to our feedback)
            candidate = None
            in_reply_to = email_data.get("in_reply_to") or email_data.get("message_id")
            feedback_email = None

            if in_reply_to:
                # Normalize Message-ID (keep as stored in DB, usually with <>)
                possible_ids = {in_reply_to.strip()}
                # Sometimes the client strips angle brackets – try without them too
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
                # We have linked feedback → find candidate by candidate_id
                try:
                    candidate = get_candidate_by_id(feedback_email.candidate_id)
                    if candidate:
                        logger.info(
                            f"Consent email linked to candidate {candidate.id} via Message-ID "
                            f"({feedback_email.message_id})"
                        )
                except Exception as e:
                    logger.warning(
                        f"Error loading candidate by id {feedback_email.candidate_id}: {e}"
                    )

            # 2) If Message-ID lookup failed, try by email address
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
            consent_value = classification == "consent_yes"
            update_candidate(candidate.id, consent_for_other_positions=consent_value)

            logger.info(
                f"Updated consent_for_other_positions for candidate {candidate.id} ({from_email}) to {consent_value}"
            )

            # Send acknowledgment
            ack_subject = "Re: " + email_data.get("subject", "Twoja wiadomość")
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

            self._send_email(to_email=from_email, subject=ack_subject, body=ack_body)

            # Notify HR about consent change (fuller picture of the situation)
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
                self._send_email(to_email=self.hr_email, subject=hr_subject, body=hr_body)
                logger.info(f"HR notified about consent change for candidate {candidate.id}")
            except Exception as e:
                logger.warning(f"Failed to notify HR about consent change: {e}")

            logger.info(f"Consent handled and acknowledgment sent to {from_email}")
            return True

        except Exception as e:
            logger.error(f"Error handling consent: {str(e)}", exc_info=True)
            return False

    def _get_rag_db(self) -> Optional[QdrantRAG]:
        """Lazy-load RAG database when needed."""
        if self.rag_db is None:
            try:
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
                azure_deployment = os.getenv(
                    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
                )
                azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

                # Prefer Qdrant server over local path (avoids locking issues)
                qdrant_host = os.getenv(
                    "QDRANT_HOST", "qdrant"
                )  # Default to service name in Docker
                qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
                qdrant_path = os.getenv("QDRANT_PATH")  # Optional, only if server not available

                if azure_api_key:
                    # Try server first, fallback to local path
                    if qdrant_host:
                        self.rag_db = QdrantRAG(
                            collection_name="recruitment_knowledge_base",
                            use_azure_openai=True,
                            azure_endpoint=azure_endpoint,
                            azure_api_key=azure_api_key,
                            azure_deployment=azure_deployment,
                            azure_api_version=azure_api_version,
                            qdrant_host=qdrant_host,
                            qdrant_port=qdrant_port,
                        )
                    elif qdrant_path:
                        self.rag_db = QdrantRAG(
                            collection_name="recruitment_knowledge_base",
                            use_azure_openai=True,
                            azure_endpoint=azure_endpoint,
                            azure_api_key=azure_api_key,
                            azure_deployment=azure_deployment,
                            azure_api_version=azure_api_version,
                            qdrant_path=qdrant_path,
                        )
                    else:
                        logger.warning("Neither QDRANT_HOST nor QDRANT_PATH set, RAG unavailable")
                        return None

                    logger.info("RAG database initialized")
                else:
                    logger.warning("Azure OpenAI API key not set, RAG unavailable")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG database: {e}")
        return self.rag_db

    def _handle_general_query(self, email_data: Dict) -> bool:
        """
        Handle general query email - classify and respond using AI or forward to HR.

        Workflow:
        1. QueryClassifierAgent decides: direct_answer, rag_answer, or forward_to_hr
        2. If direct_answer: QueryResponderAgent generates response from basic knowledge
        3. If rag_answer: QueryResponderAgent uses RAG to find relevant context, then generates response
        4. If forward_to_hr: Forward email to HR department
        """
        try:
            from_email = email_data.get("from_email", "")
            email_subject = email_data.get("subject", "")
            email_body = email_data.get("body", "")

            if not self.query_classifier or not self.query_responder:
                # Fallback: forward to HR if agents not initialized
                logger.warning("Query agents not initialized, forwarding to HR")
                return self._route_to_hr(email_data)

            # Step 1: Classify query
            logger.info(f"Classifying query from {from_email}")
            classification_result = self.query_classifier.classify_query(
                email_subject, email_body, from_email
            )

            action = classification_result.get("action", "forward_to_hr")
            reasoning = classification_result.get("reasoning", "")
            confidence = classification_result.get("confidence", 0.0)

            # Konwertuj confidence na float
            try:
                confidence = float(confidence)
            except (ValueError, TypeError):
                confidence = 0.0

            logger.info(
                f"Query classified as: {action} (confidence: {confidence:.2f}, reasoning: {reasoning})"
            )

            # CRITICAL VALIDATION: Different thresholds for different actions
            # For rag_answer: allow trying even with lower confidence (0.5+), as RAG may find the answer
            # For direct_answer: require higher confidence (0.85+)
            # For forward_to_hr or confidence < 0.5: always forward to HR
            if action == "rag_answer" and confidence < 0.5:
                logger.warning(
                    f"Confidence ({confidence:.2f}) < 0.50 for rag_answer, forwarding to HR instead"
                )
                action = "forward_to_hr"
                reasoning = f"Poziom pewności ({confidence:.2f}) jest zbyt niski dla rag_answer. {reasoning}"
            elif action == "direct_answer" and confidence < 0.7:
                # Only downgrade direct_answer to forward_to_hr on low confidence; leave forward_to_hr unchanged
                logger.warning(
                    f"Confidence ({confidence:.2f}) < 0.70 for direct_answer, forwarding to HR instead"
                )
                action = "forward_to_hr"
                reasoning = f"Poziom pewności ({confidence:.2f}) jest mniejszy niż wymagany (0.70). {reasoning}"

            # Step 2: Handle based on classification
            if action == "forward_to_hr":
                # Forward to HR - don't auto-respond
                logger.info(f"Forwarding query to HR: {reasoning}")
                return self._route_to_hr(email_data)

            elif action == "direct_answer":
                # Generate response from basic knowledge
                # ADDITIONAL VALIDATION: Check confidence again before responding
                if confidence < 0.85:
                    logger.warning(
                        f"Confidence ({confidence:.2f}) < 0.85 for direct_answer, forwarding to HR"
                    )
                    return self._route_to_hr(email_data)

                logger.info(
                    f"Generating direct answer from basic knowledge (confidence = {confidence:.2f})"
                )
                response = self.query_responder.generate_response(
                    email_subject, email_body, from_email, rag_context=None
                )

                # VALIDATION: If agent returned None, it is not confident – forward to HR
                if response is None:
                    logger.warning("Agent returned None (not confident enough), forwarding to HR")
                    return self._route_to_hr(email_data)

                # Send response to candidate
                reply_subject = (
                    f"Re: {email_subject}" if email_subject else "Odpowiedź na Twoje zapytanie"
                )
                success = self._send_email(
                    to_email=from_email, subject=reply_subject, body=response
                )

                if success:
                    logger.info(f"Direct answer sent to {from_email}")
                    # Also notify HR about the auto-response
                    self._notify_hr_about_auto_response(email_data, response, "direct_answer")

                return success

            elif action == "rag_answer":
                # For rag_answer: allow trying if confidence >= 0.5 (already validated earlier)
                # RAG may find the answer even if classification was uncertain
                logger.info(f"Generating answer using RAG (confidence = {confidence:.2f})")
                rag_db = self._get_rag_db()

                if not rag_db:
                    logger.warning("RAG database not available, forwarding to HR")
                    return self._route_to_hr(email_data)

                # Search RAG for relevant context
                query_text = f"{email_subject} {email_body}".strip()
                rag_results = rag_db.search(query_text, n_results=3)

                logger.info(f"Found {len(rag_results)} relevant documents from RAG")

                # VALIDATION: Check whether RAG found relevant documents
                if not rag_results or len(rag_results) == 0:
                    logger.warning("No relevant documents found in RAG, forwarding to HR")
                    return self._route_to_hr(email_data)

                # Generate response with RAG context
                response = self.query_responder.generate_response(
                    email_subject, email_body, from_email, rag_context=rag_results
                )

                # VALIDATION: If agent returned None, it is not confident – forward to HR
                if response is None:
                    logger.warning("Agent returned None (not confident enough), forwarding to HR")
                    return self._route_to_hr(email_data)

                # VALIDATION: Check quality of RAG response before sending
                if self.rag_validator:
                    logger.info("Validating RAG-generated response before sending")
                    validation_result = self.rag_validator.validate_rag_response(
                        generated_response=response,
                        email_subject=email_subject,
                        email_body=email_body,
                        sender_email=from_email,
                        rag_sources=rag_results,
                    )

                    if not validation_result.is_approved:
                        logger.warning(
                            f"RAG response validation FAILED for {from_email}: {validation_result.reasoning}. "
                            f"Issues: {validation_result.issues_found}, "
                            f"Factual errors: {validation_result.factual_errors}. "
                            f"Forwarding to HR instead."
                        )
                        # Forward to HR with validation details
                        return self._route_to_hr(email_data)
                    else:
                        logger.info(
                            f"RAG response validation PASSED for {from_email}: {validation_result.reasoning}"
                        )
                else:
                    logger.warning(
                        "RAG validator not available, skipping validation (sending response anyway)"
                    )

                # Send response to candidate
                reply_subject = (
                    f"Re: {email_subject}" if email_subject else "Odpowiedź na Twoje zapytanie"
                )
                success = self._send_email(
                    to_email=from_email, subject=reply_subject, body=response
                )

                if success:
                    logger.info(f"RAG-based answer sent to {from_email}")
                    # Also notify HR about the auto-response
                    self._notify_hr_about_auto_response(
                        email_data, response, "rag_answer", rag_results
                    )

                return success

            else:
                # Unknown action - forward to HR
                logger.warning(f"Unknown action: {action}, forwarding to HR")
                return self._route_to_hr(email_data)

        except Exception as e:
            logger.error(f"Error handling general query: {str(e)}", exc_info=True)
            # On error, forward to HR for manual handling
            return self._route_to_hr(email_data)

    def _notify_hr_about_auto_response(
        self,
        email_data: Dict,
        response: str,
        response_type: str,
        rag_context: Optional[list] = None,
    ):
        """Notify HR about auto-generated response."""
        try:
            hr_subject = f"[HR-AUTO] Automatyczna odpowiedź wysłana do {email_data.get('from_email', 'Nieznany')}"
            hr_body = f"""
Automatyczna odpowiedź została wygenerowana i wysłana do kandydata.

TYP ODPOWIEDZI: {response_type.upper()}
Kandydat: {email_data.get('from_email', 'Nieznany')}
Temat oryginalnego emaila: {email_data.get('subject', 'Brak tematu')}

---
ORYGINALNA WIADOMOŚĆ KANDYDATA:
---
{email_data.get('body', 'Brak treści')}

---
WYGENEROWANA ODPOWIEDŹ:
---
{response}
"""

            if rag_context:
                hr_body += "\n\n---\nUŻYTE ŹRÓDŁA Z RAG:\n---\n"
                for i, doc in enumerate(rag_context, 1):
                    hr_body += f"\n{i}. Źródło: {doc.get('metadata', {}).get('source', 'N/A')}\n"
                    hr_body += f"   Fragment: {doc.get('document', '')[:200]}...\n"

            hr_body += f"\n\n---\nMessage-ID: {email_data.get('message_id', 'Brak')}\n"

            self._send_email(to_email=self.hr_email, subject=hr_subject, body=hr_body)
            logger.info(f"HR notified about auto-response ({response_type})")
        except Exception as e:
            logger.warning(f"Failed to notify HR about auto-response: {e}")

    def _determine_ticket_priority_and_deadline(
        self, email_subject: str, email_body: str, from_email: str
    ) -> tuple:
        """
        Determine ticket priority and deadline using AI based on email content.

        Returns:
            tuple: (priority: TicketPriority, deadline_days: int) where deadline_days is between 5-14
        """
        try:
            from database.models import TicketPriority
            import json

            # Note: email_subject, from_email, email_body are user-controlled; consider sanitizing
            # or passing as a separate user message to reduce prompt injection risk in production.
            prompt = f"""
Analyze the following email inquiry and determine the appropriate ticket priority and deadline.

EMAIL:
Subject: {email_subject}
From: {from_email}
Content: {email_body}

TASK:
Determine:
1. Priority: LOW, MEDIUM, HIGH, or URGENT
   - URGENT: Time-sensitive issues, complaints, urgent requests, critical problems
   - HIGH: Important questions, status inquiries, significant concerns
   - MEDIUM: Standard questions, general inquiries, moderate importance
   - LOW: Simple questions, informational requests, low urgency

2. Deadline (in days, between 5-14 days):
   - URGENT: 5-7 days
   - HIGH: 7-10 days
   - MEDIUM: 10-12 days
   - LOW: 12-14 days

Return JSON in format:
{{
    "priority": "LOW" | "MEDIUM" | "HIGH" | "URGENT",
    "deadline_days": <number between 5-14>,
    "reasoning": "Brief explanation of the decision"
}}
"""

            if not self.ai_client or not self.model_name:
                logger.warning("AI client not available, using default priority/deadline")
                from database.models import TicketPriority

                return TicketPriority.MEDIUM, 10

            response = self.ai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in prioritizing HR inquiries and determining appropriate response deadlines.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)

            priority_str = result.get("priority", "MEDIUM").upper()
            deadline_days = result.get("deadline_days", 10)

            # Validate and clamp deadline_days to 5-14 range
            try:
                deadline_days = int(deadline_days)
                deadline_days = max(5, min(14, deadline_days))  # Clamp to 5-14
            except (ValueError, TypeError):
                deadline_days = 10  # Default

            # Map priority string to enum
            priority_map = {
                "LOW": TicketPriority.LOW,
                "MEDIUM": TicketPriority.MEDIUM,
                "HIGH": TicketPriority.HIGH,
                "URGENT": TicketPriority.URGENT,
            }
            priority = priority_map.get(priority_str, TicketPriority.MEDIUM)

            reasoning = result.get("reasoning", "No reasoning provided")
            logger.info(
                f"AI determined priority: {priority_str}, deadline: {deadline_days} days. Reasoning: {reasoning}"
            )

            return priority, deadline_days

        except Exception as e:
            logger.warning(
                f"Error determining ticket priority/deadline with AI: {str(e)}. Using defaults."
            )
            from database.models import TicketPriority

            return TicketPriority.MEDIUM, 10  # Default fallback

    def _route_to_hr(self, email_data: Dict) -> bool:
        """Route email to HR department, create ticket, and send email."""
        try:
            from datetime import datetime, timedelta
            from database.models import (
                create_ticket,
                TicketDepartment,
                get_position_by_id,
                get_all_tickets,
                get_all_candidates,
            )

            from_email = email_data.get("from_email", "Nieznany")
            message_id = email_data.get("message_id")
            email_subject = email_data.get("subject", "Brak tematu")
            email_body = email_data.get("body", "Brak treści")

            # Check for duplicates - if email was already forwarded to HR (by checking processed_emails)
            # Create unique identifier for HR forwarding
            hr_forward_id = f"hr_forward:{message_id or email_data.get('uid', '')}:{from_email}"
            if hr_forward_id in self.processed_emails:
                logger.warning(
                    f"Email {message_id or 'with UID'} from {from_email} already forwarded to HR, "
                    f"skipping duplicate"
                )
                return True  # Return True to avoid reprocessing

            # Mark as processed
            self.processed_emails.add(hr_forward_id)
            logger.debug(f"Marking HR forward {hr_forward_id} as processed")

            # Try to find related candidate (get the latest one if multiple exist)
            related_candidate_id = None
            candidate = None
            try:
                # Get all candidates with this email and take the latest one
                all_candidates = get_all_candidates()
                candidates_with_email = [
                    c for c in all_candidates if c.email.lower() == from_email.lower()
                ]
                if candidates_with_email:
                    latest_candidate = max(
                        candidates_with_email,
                        key=lambda c: (c.created_at.timestamp() if c.created_at else 0, c.id or 0),
                    )
                    related_candidate_id = latest_candidate.id
                    candidate = latest_candidate
                    logger.info(
                        f"Found candidate {related_candidate_id} ({latest_candidate.full_name}) for email {from_email}"
                    )
            except Exception as e:
                logger.warning(f"Error finding candidate for email {from_email}: {str(e)}")

            # Check if ticket already exists for this email (prevent duplicates)
            existing_ticket = None
            if message_id:
                try:
                    all_tickets = get_all_tickets()
                    existing_ticket = next(
                        (t for t in all_tickets if t.related_email_id == message_id), None
                    )
                    if existing_ticket:
                        logger.info(
                            f"Ticket #{existing_ticket.id} already exists for email {message_id}, skipping duplicate ticket creation"
                        )
                except Exception as e:
                    logger.warning(f"Error checking for existing ticket: {str(e)}")

            # Create ticket only if it doesn't exist
            if not existing_ticket:
                # Determine priority and deadline using AI
                priority, deadline_days = self._determine_ticket_priority_and_deadline(
                    email_subject, email_body, from_email
                )
                deadline = datetime.now() + timedelta(days=deadline_days)

                ticket_description = (
                    f"Email od: {from_email}\n"
                    f"Temat: {email_subject}\n\n"
                    f"Treść wiadomości:\n{email_body}\n\n"
                    f"Message-ID: {message_id or 'Brak'}"
                )

                try:
                    ticket = create_ticket(
                        department=TicketDepartment.HR,
                        priority=priority,
                        description=ticket_description,
                        deadline=deadline,
                        related_candidate_id=related_candidate_id,
                        related_email_id=message_id,
                    )
                    logger.info(
                        f"Created ticket #{ticket.id} for HR inquiry from {from_email} (priority: {priority.value}, deadline: {deadline_days} days)"
                    )
                except Exception as e:
                    logger.warning(f"Failed to create ticket for HR: {str(e)}")

            # If ticket exists, it means this email was already processed
            if existing_ticket:
                logger.info(
                    f"Email {message_id or 'with UID'} already processed (ticket #{existing_ticket.id} exists), skipping duplicate processing"
                )
                return True  # Return True to avoid reprocessing

            subject = f"[HR] {email_subject}"

            # Check if candidate exists in the database (for email content)
            candidate_info = ""
            if candidate:
                try:
                    position_info = ""
                    if candidate.position_id:
                        try:
                            position = get_position_by_id(candidate.position_id)
                            if position:
                                position_info = (
                                    f"\nStanowisko: {position.title} ({position.company})"
                                )
                        except Exception as e:
                            logger.warning(f"Error loading position {candidate.position_id}: {e}")

                    # Formatuj informacje o kandydacie
                    stage_display = {
                        "initial_screening": "Pierwsza selekcja",
                        "hr_interview": "Rozmowa HR",
                        "technical_assessment": "Weryfikacja wiedzy",
                        "final_interview": "Rozmowa końcowa",
                        "offer": "Oferta",
                    }.get(
                        (
                            candidate.stage.value
                            if hasattr(candidate.stage, "value")
                            else str(candidate.stage)
                        ),
                        str(candidate.stage),
                    )

                    status_display = {
                        "in_progress": "W trakcie",
                        "accepted": "Zaakceptowany",
                        "rejected": "Odrzucony",
                    }.get(
                        (
                            candidate.status.value
                            if hasattr(candidate.status, "value")
                            else str(candidate.status)
                        ),
                        str(candidate.status),
                    )

                    consent_info = ""
                    if candidate.consent_for_other_positions is not None:
                        consent_info = f"\nZgoda na inne rekrutacje: {'Tak' if candidate.consent_for_other_positions else 'Nie'}"

                    candidate_info = f"""
---
INFORMACJE O KANDYDACIE (znaleziony w bazie danych):
---
ID kandydata: {candidate.id}
Imię i nazwisko: {candidate.full_name}
Email: {candidate.email}
Status: {status_display}
Etap rekrutacji: {stage_display}{position_info}{consent_info}
Link do profilu: http://localhost:5000/candidate/{candidate.id} (lub odpowiedni URL w produkcji)
---
"""
                    logger.info(
                        f"Found candidate {candidate.id} ({candidate.full_name}) for email {from_email}"
                    )
                except Exception as e:
                    logger.warning(f"Error formatting candidate info: {str(e)}")
                    candidate_info = ""
            else:
                logger.debug(f"No candidate found in database for email {from_email}")

            # Ensure body is not empty - if email_body is empty, add default message
            email_body = email_data.get("body", "")
            if not email_body or not email_body.strip():
                email_body = "(Brak treści w oryginalnej wiadomości)"
                logger.warning(f"Empty email body from {from_email}, using default message")

            body = f"""
Email otrzymany od: {from_email}
Data: {email_data.get('date', 'Nieznana')}
Temat: {email_data.get('subject', 'Brak tematu')}
{candidate_info}
---
Treść wiadomości:
---

{email_body}

---
Oryginalny Message-ID: {email_data.get('message_id', 'Brak')}
In-Reply-To: {email_data.get('in_reply_to', 'Brak')}
"""

            success = self._send_email(
                to_email=self.hr_email, subject=subject, body=body, reply_to=from_email
            )

            # Send acknowledgment to original sender (always, even if forwarding to HR failed)
            # Ticket was created, so candidate should be notified
            ack_subject = "Re: " + email_subject
            ack_body = """
Dziękujemy za kontakt.

Twoja wiadomość została przekazana do działu HR w celu rozpatrzenia.

Otrzymasz odpowiedź w najkrótszym możliwym terminie.

Z wyrazami szacunku

Dział HR
"""
            ack_success = self._send_email(to_email=from_email, subject=ack_subject, body=ack_body)

            if success:
                if ack_success:
                    if candidate_info:
                        logger.info(
                            f"Email routed to HR and acknowledgment sent to {from_email} (candidate ID: {candidate.id if candidate else 'N/A'})"
                        )
                    else:
                        logger.info(f"Email routed to HR and acknowledgment sent to {from_email}")
                else:
                    logger.warning(
                        f"Email routed to HR, but failed to send acknowledgment to {from_email}"
                    )
            else:
                if ack_success:
                    logger.warning(
                        f"Failed to send email to HR for {from_email}, but acknowledgment sent to candidate"
                    )
                else:
                    logger.error(f"Failed to send email to HR and acknowledgment to {from_email}")

            # Return True if either forwarding or acknowledgment succeeded (ticket was created)
            return success or ack_success

        except Exception as e:
            logger.error(f"Error routing email to HR: {str(e)}", exc_info=True)
            return False

    def _send_email(
        self, to_email: str, subject: str, body: str, reply_to: Optional[str] = None
    ) -> bool:
        """Send email via SMTP."""
        try:
            # Validate email content - prevent sending empty emails
            if not body or not body.strip():
                logger.warning(
                    f"Attempted to send empty email to {to_email} with subject: {subject}. Skipping."
                )
                return False

            if not subject or not subject.strip():
                logger.warning(
                    f"Attempted to send email to {to_email} with empty subject. Skipping."
                )
                return False

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_username
            msg["To"] = to_email
            if reply_to:
                msg["Reply-To"] = reply_to

            # Add text content
            text_part = MIMEText(body, "plain", "utf-8")
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

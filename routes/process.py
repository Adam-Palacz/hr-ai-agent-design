"""Process feedback (accept/reject) route."""

import json
import threading
from pathlib import Path
from flask import request, redirect, url_for, flash

from config import settings
from core.logger import logger
from database.models import (
    get_candidate_by_id,
    create_hr_note,
    update_candidate,
    get_hr_notes_for_candidate,
    get_position_by_id,
    save_feedback_email,
    get_model_responses_for_candidate,
    save_validation_error,
    CandidateStatus,
    RecruitmentStage,
)
from models.feedback_models import HRFeedback, Decision, FeedbackFormat
from agents.cv_parser_agent import CVParserAgent
from agents.feedback_agent import FeedbackAgent
from services.cv_service import CVService
from services.feedback_service import FeedbackService
from services.email_sender import send_email_gmail
from routes.helpers import get_next_stage


def register_process(app):
    """Register process feedback route."""

    @app.route("/process", methods=["POST"])
    def process_feedback():
        """Process CV and generate feedback."""
        candidate_id = request.form.get("candidate_id")
        if not candidate_id:
            flash("Brak ID kandydata", "error")
            return redirect(url_for("index"))
        try:
            candidate_id = int(candidate_id)
        except ValueError:
            flash("Nieprawidłowe ID kandydata", "error")
            return redirect(url_for("index"))

        candidate = get_candidate_by_id(candidate_id)
        if not candidate:
            flash("Kandydat nie został znaleziony", "error")
            return redirect(url_for("index"))

        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        filename = request.form.get("filename")
        notes = request.form.get("notes", "").strip()
        decision = request.form.get("decision")
        candidate_email = request.form.get("candidate_email", "").strip()

        if not filename or not notes or not decision:
            flash("Wypełnij wszystkie wymagane pola", "error")
            return redirect(url_for("candidate_detail", candidate_id=candidate_id))

        current_stage = (
            candidate.stage
            if isinstance(candidate.stage, RecruitmentStage)
            else RecruitmentStage(
                candidate.stage.value if hasattr(candidate.stage, "value") else str(candidate.stage)
            )
        )

        if not notes or not notes.strip():
            flash("Notatka HR jest wymagana", "error")
            return redirect(url_for("candidate_detail", candidate_id=candidate_id))

        try:
            create_hr_note(
                candidate_id=candidate_id,
                notes=notes.strip(),
                stage=current_stage,
                created_by="HR Team",
            )
            logger.info(
                f"Saved HR note for candidate {candidate_id} at stage {current_stage.value}"
            )
        except Exception as e:
            logger.error(f"Could not save HR note: {str(e)}", exc_info=True)
            flash(f"Błąd podczas zapisywania notatki HR: {str(e)}", "error")
            return redirect(url_for("candidate_detail", candidate_id=candidate_id))

        if decision == "accepted":
            next_stage = get_next_stage(current_stage)
            try:
                update_candidate(
                    candidate_id, status=CandidateStatus.ACCEPTED.value, stage=next_stage.value
                )
                logger.info(
                    f"Candidate {candidate_id} accepted, moved from {current_stage.value} to {next_stage.value}"
                )
                stage_display = {
                    "initial_screening": "Pierwsza selekcja",
                    "hr_interview": "Rozmowa HR",
                    "technical_assessment": "Weryfikacja wiedzy",
                    "final_interview": "Rozmowa końcowa",
                    "offer": "Oferta",
                }.get(next_stage.value, next_stage.value)
                flash(
                    f"Kandydat został zaakceptowany i przeszedł do etapu: {stage_display}",
                    "success",
                )
                return redirect(url_for("candidate_detail", candidate_id=candidate_id))
            except Exception as e:
                logger.error(f"Could not update candidate status/stage: {str(e)}", exc_info=True)
                flash(f"Błąd podczas aktualizacji kandydata: {str(e)}", "error")
                return redirect(url_for("candidate_detail", candidate_id=candidate_id))

        elif decision == "rejected":
            filepath = Path(candidate.cv_path) if candidate.cv_path else upload_folder / filename
            if not filepath.exists():
                flash("Plik nie został znaleziony", "error")
                return redirect(url_for("candidate_detail", candidate_id=candidate_id))

            try:
                update_candidate(
                    candidate_id, status=CandidateStatus.REJECTED.value, stage=current_stage.value
                )
                logger.info(
                    f"Updated candidate {candidate_id}: status=rejected, stage={current_stage.value}"
                )
            except Exception as e:
                logger.warning(f"Could not update candidate status/stage: {str(e)}")

            def process_feedback_background():
                try:
                    logger.info(
                        f"[Background] Initializing agents for feedback generation for candidate {candidate_id}..."
                    )
                    cv_parser = CVParserAgent(
                        model_name=settings.openai_model,
                        vision_model_name=settings.azure_openai_vision_deployment,
                        use_ocr=settings.use_ocr,
                        temperature=settings.openai_temperature,
                        api_key=settings.api_key,
                        timeout=settings.openai_timeout,
                        max_retries=settings.openai_max_retries,
                    )
                    feedback_agent = FeedbackAgent(
                        model_name=settings.openai_model,
                        temperature=settings.openai_feedback_temperature,
                        api_key=settings.api_key,
                        timeout=settings.openai_timeout,
                        max_retries=settings.openai_max_retries,
                    )
                    from agents.validation_agent import FeedbackValidatorAgent
                    from agents.correction_agent import FeedbackCorrectionAgent

                    validator_agent = FeedbackValidatorAgent(
                        model_name=settings.openai_model,
                        temperature=0.0,
                        api_key=settings.api_key,
                        timeout=settings.openai_timeout,
                        max_retries=settings.openai_max_retries,
                    )
                    correction_agent = FeedbackCorrectionAgent(
                        model_name=settings.openai_model,
                        temperature=0.3,
                        api_key=settings.api_key,
                        timeout=settings.openai_timeout,
                        max_retries=settings.openai_max_retries,
                    )
                    cv_service = CVService(cv_parser)
                    feedback_service = FeedbackService(
                        feedback_agent,
                        validator_agent=validator_agent,
                        correction_agent=correction_agent,
                        max_validation_iterations=3,
                    )

                    logger.info(f"[Background] Processing CV for feedback generation: {filename}")
                    cv_data = cv_service.process_cv_from_pdf(
                        str(filepath), verbose=False, candidate_id=candidate_id
                    )

                    from models.job_models import JobOffer

                    candidate_ref = get_candidate_by_id(candidate_id)
                    if candidate_ref and candidate_ref.position_id:
                        position = get_position_by_id(candidate_ref.position_id)
                        if position:
                            job_offer = JobOffer(
                                title=position.title,
                                company=position.company,
                                location="",
                                description=position.description or "",
                            )
                            logger.info(
                                f"[Background] Using job offer from database: {job_offer.title} at {job_offer.company}"
                            )
                        else:
                            logger.warning(
                                f"[Background] Position ID {candidate_ref.position_id} not found in database"
                            )
                            job_offer = JobOffer(
                                title="Position", company="", location="", description=""
                            )
                    else:
                        logger.warning(
                            f"[Background] Candidate {candidate_id} has no position_id assigned"
                        )
                        job_offer = JobOffer(
                            title="Position", company="", location="", description=""
                        )

                    hr_notes_list = get_hr_notes_for_candidate(candidate_id)
                    all_notes = []
                    if hr_notes_list:
                        for note in hr_notes_list:
                            stage_name = (
                                note.stage.value
                                if isinstance(note.stage, RecruitmentStage)
                                else note.stage
                            )
                            stage_display = {
                                "initial_screening": "Pierwsza selekcja",
                                "hr_interview": "Rozmowa HR",
                                "technical_assessment": "Weryfikacja wiedzy",
                                "final_interview": "Rozmowa końcowa",
                                "offer": "Oferta",
                            }.get(stage_name, stage_name)
                            note_date = (
                                note.created_at.strftime("%Y-%m-%d %H:%M")
                                if note.created_at
                                else "N/A"
                            )
                            all_notes.append(f"[{stage_display} - {note_date}]\n{note.notes}")
                    combined_notes = "\n\n---\n\n".join(all_notes) if all_notes else notes

                    hr_feedback = HRFeedback(
                        decision=Decision.REJECTED,
                        notes=combined_notes,
                        position_applied=job_offer.title if job_offer else "Position",
                        interviewer_name="HR Team",
                    )

                    stage_display = {
                        "initial_screening": "Pierwsza selekcja",
                        "hr_interview": "Rozmowa HR",
                        "technical_assessment": "Weryfikacja wiedzy",
                        "final_interview": "Rozmowa końcowa",
                        "offer": "Oferta",
                    }.get(current_stage.value, current_stage.value)

                    logger.info(
                        f"[Background] Generating feedback for rejected candidate ID: {candidate_id} at stage: {stage_display}"
                    )
                    candidate_feedback, is_validated, validation_error_info = (
                        feedback_service.generate_feedback(
                            cv_data,
                            hr_feedback,
                            job_offer=job_offer,
                            output_format=FeedbackFormat.HTML,
                            save_to_file=False,
                            candidate_id=candidate_id,
                            recruitment_stage=stage_display,
                        )
                    )

                    if not is_validated and validation_error_info:
                        logger.error(
                            f"[Background] Validation failed for candidate {candidate_id}. Saving error to database."
                        )
                        model_responses = get_model_responses_for_candidate(candidate_id)
                        model_responses_summary = [
                            {
                                "agent_type": resp.agent_type,
                                "model_name": resp.model_name,
                                "created_at": (
                                    resp.created_at.isoformat() if resp.created_at else None
                                ),
                            }
                            for resp in model_responses
                        ]
                        total_validations = validation_error_info.get(
                            "total_validations",
                            len(validation_error_info.get("validation_results", [])),
                        )
                        total_corrections = validation_error_info.get("total_corrections", 0)
                        last_validation = validation_error_info.get(
                            "last_validation_number", total_validations
                        )
                        last_correction = validation_error_info.get(
                            "last_correction_number", total_corrections
                        )
                        error_message = (
                            f"Validation failed after {feedback_service.max_iterations} iterations. "
                            f"Feedback was not approved by validator. "
                            f"Total validations performed: {total_validations}, "
                            f"Total corrections performed: {total_corrections}, "
                            f"Last validation number: {last_validation}, "
                            f"Last correction number: {last_correction}"
                        )
                        save_validation_error(
                            candidate_id=candidate_id,
                            error_message=error_message,
                            feedback_html_content=candidate_feedback.html_content,
                            validation_results=json.dumps(
                                validation_error_info.get("validation_results", []),
                                ensure_ascii=False,
                                indent=2,
                            ),
                            model_responses_summary=json.dumps(
                                model_responses_summary, ensure_ascii=False, indent=2
                            ),
                        )
                        logger.error(
                            f"[Background] Validation error saved for candidate {candidate_id}. Email will NOT be sent."
                        )
                        return

                    candidate_ref = get_candidate_by_id(candidate_id)
                    consent_value = (
                        getattr(candidate_ref, "consent_for_other_positions", None)
                        if candidate_ref
                        else None
                    )
                    html_content = feedback_service.get_feedback_html(
                        candidate_feedback, consent_for_other_positions=consent_value
                    )

                    message_id = None
                    if candidate_email:
                        subject = f"Odpowiedź na aplikację - {job_offer.title if job_offer else 'Stanowisko'}"
                        if not settings.email_username or not settings.email_password:
                            logger.warning(
                                f"[Background] Email not sent - Email credentials not configured for candidate {candidate_id}"
                            )
                        else:
                            success, message_id = send_email_gmail(
                                candidate_email, subject, html_content
                            )
                            if success:
                                logger.info(
                                    f"[Background] Email sent successfully to {candidate_email} for candidate {candidate_id} with Message-ID: {message_id}"
                                )
                            else:
                                logger.error(
                                    f"[Background] Failed to send email to {candidate_email} for candidate {candidate_id}"
                                )

                    try:
                        save_feedback_email(candidate_id, html_content, message_id=message_id)
                        logger.info(
                            f"[Background] Feedback email saved to database for candidate {candidate_id} with Message-ID: {message_id}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[Background] Could not save feedback email: {str(e)}", exc_info=True
                        )

                    logger.info(
                        f"[Background] Feedback processing completed for candidate {candidate_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"[Background] Error processing CV and generating feedback for candidate {candidate_id}: {str(e)}",
                        exc_info=True,
                    )

            thread = threading.Thread(target=process_feedback_background, daemon=True)
            thread.start()

            flash(
                "Kandydat został odrzucony. Generowanie feedbacku i wysyłanie emaila odbywa się w tle. Sprawdź logi lub historię emaili, aby zobaczyć status.",
                "success",
            )
            return redirect(url_for("candidate_detail", candidate_id=candidate_id))

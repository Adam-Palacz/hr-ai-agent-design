"""Simple web application for HR to review CVs and send feedback emails."""
import os
import smtplib
import threading
import json
from datetime import datetime
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, Response
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from config import settings
from config.job_config import load_job_config, create_job_offer_from_config
from core.logger import logger, setup_logger
from agents.cv_parser_agent import CVParserAgent
from agents.feedback_agent import FeedbackAgent
from agents.validation_agent import FeedbackValidatorAgent
from agents.correction_agent import FeedbackCorrectionAgent
from services.cv_service import CVService
from services.feedback_service import FeedbackService
from services.metrics_service import metrics_service
from models.feedback_models import HRFeedback, Decision, FeedbackFormat
from database.models import (
    init_db, get_all_candidates, get_candidate_by_id, create_candidate,
    update_candidate, save_feedback_email, get_feedback_emails_for_candidate,
    get_all_feedback_emails, get_feedback_email_by_message_id,
    save_model_response, get_model_responses_for_candidate, get_all_model_responses,
    CandidateStatus, RecruitmentStage, 
    get_all_positions, create_position, get_position_by_id, update_position, delete_position,
    HRNote, create_hr_note, get_hr_notes_for_candidate, get_all_hr_notes,
    Ticket, TicketStatus, TicketPriority, TicketDepartment,
    create_ticket, get_ticket_by_id, get_all_tickets, update_ticket, delete_ticket
)

# Load environment variables
load_dotenv()

# Setup logging
setup_logger(log_level=settings.log_level)

# Initialize database
init_db()

# Seed database with example data if empty
try:
    from database.seed_data import seed_database
    seed_database()
except Exception as e:
    logger.warning(f"Could not seed database: {str(e)}")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Check email configuration on startup
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
    logger.info(f"Email configured for: {settings.email_username} (SMTP: {settings.smtp_host}:{settings.smtp_port}, IMAP: {settings.imap_host}:{settings.imap_port})")

# Initialize email monitor if configured and enabled
email_monitor = None
if settings.email_monitor_enabled and settings.email_username and settings.email_password and settings.iod_email and settings.hr_email:
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
            check_interval=settings.email_check_interval
        )
        email_monitor.start()
        logger.info(f"Email monitor started (IOD: {settings.iod_email}, HR: {settings.hr_email}, interval: {settings.email_check_interval}s)")
    except Exception as e:
        logger.warning(f"Failed to start email monitor: {str(e)}")
elif settings.email_monitor_enabled and settings.email_username and settings.email_password:
    logger.warning(
        "Email monitoring disabled. To enable, add to .env file:\n"
        "  IOD_EMAIL=iod@company.com\n"
        "  HR_EMAIL=hr@company.com\n"
        "  EMAIL_CHECK_INTERVAL=60  # optional, default 60 seconds"
    )


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_next_stage(current_stage: RecruitmentStage) -> RecruitmentStage:
    """Get next recruitment stage."""
    stage_order = [
        RecruitmentStage.INITIAL_SCREENING,
        RecruitmentStage.HR_INTERVIEW,
        RecruitmentStage.TECHNICAL_ASSESSMENT,
        RecruitmentStage.FINAL_INTERVIEW,
        RecruitmentStage.OFFER
    ]
    
    try:
        current_index = stage_order.index(current_stage)
        if current_index < len(stage_order) - 1:
            return stage_order[current_index + 1]
        else:
            # Already at last stage, stay there
            return current_stage
    except ValueError:
        # Unknown stage, default to next after initial
        return RecruitmentStage.HR_INTERVIEW


def send_email_gmail(to_email: str, subject: str, html_content: str, message_id: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """
    Send email using Gmail SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        message_id: Optional Message-ID (if not provided, will be generated)
        
    Returns:
        Tuple of (success: bool, message_id: Optional[str])
    """
    if not settings.email_username or not settings.email_password:
        logger.error("Email credentials not configured. Set EMAIL_USERNAME and EMAIL_PASSWORD in .env")
        return False, None
    
    try:
        import uuid
        import socket
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.email_username
        msg['To'] = to_email
        
        # Generate Message-ID if not provided
        if not message_id:
            # Generate a unique Message-ID following RFC 5322 format
            domain = settings.email_username.split('@')[1] if '@' in settings.email_username else socket.getfqdn()
            message_id = f"<{uuid.uuid4().hex}@{domain}>"
        
        msg['Message-ID'] = message_id
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Send email via SMTP (using settings)
        if settings.smtp_port == 465:
            # Use SSL for port 465
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
                server.login(settings.email_username, settings.email_password)
                server.send_message(msg)
        else:
            # Use TLS for port 587
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(settings.email_username, settings.email_password)
                server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email} via Gmail with Message-ID: {message_id}")
        return True, message_id
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False, None


@app.route('/')
def index():
    """Main page with list of candidates."""
    candidates = get_all_candidates()
    positions = get_all_positions()
    
    # Create position lookup dictionary
    position_dict = {pos.id: pos for pos in positions}
    
    # Add position information to each candidate
    for candidate in candidates:
        if candidate.position_id and candidate.position_id in position_dict:
            position = position_dict[candidate.position_id]
            candidate.position_title = position.title
            candidate.position_company = position.company
        else:
            candidate.position_title = None
            candidate.position_company = None
    
    return render_template('candidates_list.html', candidates=candidates)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle PDF upload."""
    if 'pdf_file' not in request.files:
        flash('Brak pliku PDF', 'error')
        return redirect(url_for('index'))
    
    file = request.files['pdf_file']
    if file.filename == '':
        flash('Nie wybrano pliku', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = UPLOAD_FOLDER / filename
        file.save(str(filepath))
        
        logger.info(f"PDF uploaded: {filename}")
        return redirect(url_for('review', filename=filename))
    else:
        flash('Nieprawidłowy format pliku. Dozwolone tylko PDF.', 'error')
        return redirect(url_for('index'))


@app.route('/candidate/<int:candidate_id>')
def candidate_detail(candidate_id):
    """Candidate detail page with PDF viewer and feedback form."""
    candidate = get_candidate_by_id(candidate_id)
    if not candidate:
        flash('Kandydat nie został znaleziony', 'error')
        return redirect(url_for('index'))
    
    # Check if CV file exists
    if not candidate.cv_path:
        flash('Brak pliku CV dla tego kandydata', 'error')
        return redirect(url_for('index'))
    
    filepath = Path(candidate.cv_path)
    if not filepath.exists():
        flash('Plik CV nie został znaleziony', 'error')
        return redirect(url_for('index'))
    
    # Use relative path from uploads folder if possible, otherwise use absolute path
    try:
        filename = filepath.relative_to(UPLOAD_FOLDER).as_posix()
    except ValueError:
        # If not in uploads folder, copy to uploads or use absolute path
        filename = filepath.name
        # Copy to uploads if not already there
        if not (UPLOAD_FOLDER / filename).exists():
            import shutil
            shutil.copy2(str(filepath), str(UPLOAD_FOLDER / filename))
            filename = filename
    
    # Get feedback emails for this candidate
    feedback_emails = get_feedback_emails_for_candidate(candidate_id)
    
    # Create job offer from candidate's position in database
    job_offer = None
    if candidate.position_id:
        # Get position from database
        position = get_position_by_id(candidate.position_id)
        if position:
            from models.job_models import JobOffer
            job_offer = JobOffer(
                title=position.title,
                company=position.company,
                location="",
                description=position.description or ""
            )
            logger.info(f"Loaded job offer from database: {job_offer.title} at {job_offer.company}")
        else:
            logger.warning(f"Position ID {candidate.position_id} not found in database")
    
    # Get HR notes for this candidate
    hr_notes = get_hr_notes_for_candidate(candidate_id)
    
    return render_template('review.html', 
                         candidate=candidate,
                         filename=filename,
                         job_offer=job_offer,
                         feedback_emails=feedback_emails,
                         hr_notes=hr_notes)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded PDF files."""
    # Try to find file in uploads folder first
    filepath = UPLOAD_FOLDER / filename
    if filepath.exists():
        return send_from_directory(str(UPLOAD_FOLDER), filename)
    
    # If not found, try to find in candidate's cv_path
    # This handles cases where CV is stored elsewhere
    return send_from_directory(str(UPLOAD_FOLDER), filename)


@app.route('/add_candidate', methods=['GET', 'POST'])
def add_candidate():
    """Add a new candidate."""
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        position_id = request.form.get('position_id', '').strip()
        cv_file = request.files.get('cv_file')
        
        if not first_name or not last_name or not email:
            flash('Wypełnij wszystkie wymagane pola', 'error')
            return redirect(url_for('add_candidate'))
        
        # Save CV file if provided
        cv_path = None
        if cv_file and cv_file.filename and allowed_file(cv_file.filename):
            filename = secure_filename(cv_file.filename)
            filepath = UPLOAD_FOLDER / filename
            filepath.parent.mkdir(exist_ok=True)
            cv_file.save(str(filepath))
            cv_path = str(filepath)
        
        # Handle consent_for_other_positions
        consent_value = request.form.get('consent_for_other_positions', '').strip()
        if consent_value not in ('1', '0'):
            flash('Wybierz zgodę na rozważenie do innych stanowisk (Tak/Nie)', 'error')
            return redirect(url_for('add_candidate'))
        consent_bool = True if consent_value == '1' else False
        
        # Create candidate
        position_id_int = int(position_id) if position_id else None
        create_candidate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            position_id=position_id_int,
            cv_path=cv_path,
            consent_for_other_positions=consent_bool
        )
        
        flash('Kandydat został dodany', 'success')
        return redirect(url_for('index'))
    
    # GET request - show form
    positions = get_all_positions()
    return render_template('add_candidate.html', positions=positions)


@app.route('/candidate/<int:candidate_id>/edit', methods=['GET', 'POST'])
def edit_candidate(candidate_id):
    """Edit candidate information."""
    candidate = get_candidate_by_id(candidate_id)
    if not candidate:
        flash('Kandydat nie został znaleziony', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        position_id = request.form.get('position_id', '').strip()
        cv_file = request.files.get('cv_file')
        
        if not first_name or not last_name or not email:
            flash('Wypełnij wszystkie wymagane pola', 'error')
            return redirect(url_for('edit_candidate', candidate_id=candidate_id))
        
        # Update CV file if provided
        cv_path = candidate.cv_path
        if cv_file and cv_file.filename and allowed_file(cv_file.filename):
            filename = secure_filename(cv_file.filename)
            filepath = UPLOAD_FOLDER / filename
            filepath.parent.mkdir(exist_ok=True)
            cv_file.save(str(filepath))
            cv_path = str(filepath)
        
        # Update candidate
        position_id_int = int(position_id) if position_id else None
        
        # Handle consent_for_other_positions
        consent_value = request.form.get('consent_for_other_positions', '').strip()
        if consent_value not in ('1', '0'):
            flash('Wybierz zgodę na rozważenie do innych stanowisk (Tak/Nie)', 'error')
            return redirect(url_for('edit_candidate', candidate_id=candidate_id))
        consent_bool = True if consent_value == '1' else False
        
        update_candidate(
            candidate_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            position_id=position_id_int,
            cv_path=cv_path,
            consent_for_other_positions=consent_bool
        )
        
        flash('Kandydat został zaktualizowany', 'success')
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))
    
    # GET request - show form
    positions = get_all_positions()
    return render_template('edit_candidate.html', candidate=candidate, positions=positions)


@app.route('/positions')
def positions_list():
    """List all positions."""
    positions = get_all_positions()
    return render_template('positions_list.html', positions=positions)


@app.route('/positions/add', methods=['GET', 'POST'])
def add_position():
    """Add a new position."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company = request.form.get('company', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title or not company:
            flash('Wypełnij wszystkie wymagane pola', 'error')
            return redirect(url_for('add_position'))
        
        create_position(title=title, company=company, description=description)
        flash('Pozycja została dodana', 'success')
        return redirect(url_for('positions_list'))
    
    return render_template('add_position.html')


@app.route('/positions/<int:position_id>/edit', methods=['GET', 'POST'])
def edit_position(position_id):
    """Edit a position."""
    position = get_position_by_id(position_id)
    if not position:
        flash('Pozycja nie została znaleziona', 'error')
        return redirect(url_for('positions_list'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company = request.form.get('company', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title or not company:
            flash('Wypełnij wszystkie wymagane pola', 'error')
            return redirect(url_for('edit_position', position_id=position_id))
        
        update_position(position_id, title=title, company=company, description=description)
        flash('Pozycja została zaktualizowana', 'success')
        return redirect(url_for('positions_list'))
    
    return render_template('edit_position.html', position=position)


@app.route('/positions/<int:position_id>/delete', methods=['POST'])
def delete_position_route(position_id):
    """Delete a position."""
    if delete_position(position_id):
        flash('Pozycja została usunięta', 'success')
    else:
        flash('Nie można usunąć pozycji', 'error')
    return redirect(url_for('positions_list'))


@app.route('/tickets')
def tickets_list():
    """List all tickets."""
    tickets = get_all_tickets()
    
    # Get candidate information for tickets
    candidates_dict = {c.id: c for c in get_all_candidates()}
    for ticket in tickets:
        if ticket.related_candidate_id and ticket.related_candidate_id in candidates_dict:
            ticket.candidate = candidates_dict[ticket.related_candidate_id]
        else:
            ticket.candidate = None
    
    return render_template('tickets_list.html', tickets=tickets)


@app.route('/tickets/add', methods=['GET', 'POST'])
def add_ticket():
    """Add a new ticket."""
    if request.method == 'POST':
        department = request.form.get('department', '').strip()
        priority = request.form.get('priority', '').strip()
        status = request.form.get('status', '').strip()
        description = request.form.get('description', '').strip()
        deadline_str = request.form.get('deadline', '').strip()
        
        if not department or not priority or not description:
            flash('Wypełnij wszystkie wymagane pola', 'error')
            return redirect(url_for('add_ticket'))
        
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace('T', ' '))
            except ValueError:
                flash('Nieprawidłowy format daty deadline', 'error')
                return redirect(url_for('add_ticket'))
        
        create_ticket(
            department=TicketDepartment(department),
            priority=TicketPriority(priority),
            status=TicketStatus(status) if status else TicketStatus.OPEN,
            description=description,
            deadline=deadline
        )
        
        flash('Ticket został utworzony', 'success')
        return redirect(url_for('tickets_list'))
    
    return render_template('add_ticket.html')


@app.route('/tickets/<int:ticket_id>/edit', methods=['GET', 'POST'])
def edit_ticket(ticket_id):
    """Edit a ticket."""
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        flash('Ticket nie został znaleziony', 'error')
        return redirect(url_for('tickets_list'))
    
    if request.method == 'POST':
        department = request.form.get('department', '').strip()
        priority = request.form.get('priority', '').strip()
        status = request.form.get('status', '').strip()
        description = request.form.get('description', '').strip()
        deadline_str = request.form.get('deadline', '').strip()
        
        if not department or not priority or not description:
            flash('Wypełnij wszystkie wymagane pola', 'error')
            return redirect(url_for('edit_ticket', ticket_id=ticket_id))
        
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace('T', ' '))
            except ValueError:
                flash('Nieprawidłowy format daty deadline', 'error')
                return redirect(url_for('edit_ticket', ticket_id=ticket_id))
        
        update_ticket(
            ticket_id,
            department=TicketDepartment(department),
            priority=TicketPriority(priority),
            status=TicketStatus(status) if status else None,
            description=description,
            deadline=deadline
        )
        
        flash('Ticket został zaktualizowany', 'success')
        return redirect(url_for('tickets_list'))
    
    return render_template('edit_ticket.html', ticket=ticket)


@app.route('/tickets/<int:ticket_id>/delete', methods=['POST'])
def delete_ticket_route(ticket_id):
    """Delete a ticket."""
    if delete_ticket(ticket_id):
        flash('Ticket został usunięty', 'success')
    else:
        flash('Nie można usunąć ticketu', 'error')
    return redirect(url_for('tickets_list'))


@app.route('/candidate/<int:candidate_id>/delete', methods=['POST'])
def delete_candidate_route(candidate_id):
    """Delete a candidate."""
    from database.models import delete_candidate
    
    if delete_candidate(candidate_id):
        flash('Kandydat został usunięty', 'success')
    else:
        flash('Nie można usunąć kandydata', 'error')
    return redirect(url_for('index'))


@app.route('/process', methods=['POST'])
def process_feedback():
    """Process CV and generate feedback."""
    candidate_id = request.form.get('candidate_id')
    if not candidate_id:
        flash('Brak ID kandydata', 'error')
        return redirect(url_for('index'))
    
    try:
        candidate_id = int(candidate_id)
    except ValueError:
        flash('Nieprawidłowe ID kandydata', 'error')
        return redirect(url_for('index'))
    
    candidate = get_candidate_by_id(candidate_id)
    if not candidate:
        flash('Kandydat nie został znaleziony', 'error')
        return redirect(url_for('index'))
    
    filename = request.form.get('filename')
    notes = request.form.get('notes', '').strip()
    decision = request.form.get('decision')
    candidate_email = request.form.get('candidate_email', '').strip()
    stage = request.form.get('stage', '')
    
    if not filename or not notes or not decision:
        flash('Wypełnij wszystkie wymagane pola', 'error')
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))
    
    # Use candidate's current stage (not from form - it's read-only)
    current_stage = candidate.stage if isinstance(candidate.stage, RecruitmentStage) else RecruitmentStage(candidate.stage.value if hasattr(candidate.stage, 'value') else str(candidate.stage))
    
    # CRITICAL: Always save HR note to database (for both accepted and rejected)
    if not notes or not notes.strip():
        flash('Notatka HR jest wymagana', 'error')
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))
    
    # Save current note to database - ALWAYS
    try:
        create_hr_note(
            candidate_id=candidate_id,
            notes=notes.strip(),
            stage=current_stage,
            created_by="HR Team"
        )
        logger.info(f"Saved HR note for candidate {candidate_id} at stage {current_stage.value}")
    except Exception as e:
        logger.error(f"Could not save HR note: {str(e)}", exc_info=True)
        flash(f'Błąd podczas zapisywania notatki HR: {str(e)}', 'error')
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))
    
    # Handle decision: ACCEPTED = move to next stage, REJECTED = generate feedback
    if decision == 'accepted':
        # ACCEPTED: Move to next stage, don't generate feedback
        next_stage = _get_next_stage(current_stage)
        
        # Update candidate status and stage
        try:
            update_candidate(
                candidate_id,
                status=CandidateStatus.ACCEPTED.value,
                stage=next_stage.value
            )
            logger.info(f"Candidate {candidate_id} accepted, moved from {current_stage.value} to {next_stage.value}")
            
            stage_display = {
                'initial_screening': 'Pierwsza selekcja',
                'hr_interview': 'Rozmowa HR',
                'technical_assessment': 'Weryfikacja wiedzy',
                'final_interview': 'Rozmowa końcowa',
                'offer': 'Oferta'
            }.get(next_stage.value, next_stage.value)
            
            flash(f'Kandydat został zaakceptowany i przeszedł do etapu: {stage_display}', 'success')
            return redirect(url_for('candidate_detail', candidate_id=candidate_id))
        except Exception as e:
            logger.error(f"Could not update candidate status/stage: {str(e)}", exc_info=True)
            flash(f'Błąd podczas aktualizacji kandydata: {str(e)}', 'error')
            return redirect(url_for('candidate_detail', candidate_id=candidate_id))
        
    elif decision == 'rejected':
        # REJECTED: Generate feedback and send email in background
        # Only now we need to parse CV and generate feedback
        
        filepath = Path(candidate.cv_path) if candidate.cv_path else UPLOAD_FOLDER / filename
        if not filepath.exists():
            flash('Plik nie został znaleziony', 'error')
            return redirect(url_for('candidate_detail', candidate_id=candidate_id))
        
        # Update candidate status to REJECTED immediately
        try:
            update_candidate(
                candidate_id,
                status=CandidateStatus.REJECTED.value,
                stage=current_stage.value
            )
            logger.info(f"Updated candidate {candidate_id}: status=rejected, stage={current_stage.value}")
        except Exception as e:
            logger.warning(f"Could not update candidate status/stage: {str(e)}")
        
        # Start background processing
        def process_feedback_background():
            """Process feedback generation and email sending in background."""
            try:
                # Initialize agents (only for rejected candidates)
                logger.info(f"[Background] Initializing agents for feedback generation for candidate {candidate_id}...")
                cv_parser = CVParserAgent(
                    model_name=settings.openai_model,
                    vision_model_name=settings.azure_openai_vision_deployment,
                    use_ocr=settings.use_ocr,
                    temperature=settings.openai_temperature,
                    api_key=settings.api_key,
                    timeout=settings.openai_timeout,
                    max_retries=settings.openai_max_retries
                )
                
                feedback_agent = FeedbackAgent(
                    model_name=settings.openai_model,
                    temperature=settings.openai_feedback_temperature,
                    api_key=settings.api_key,
                    timeout=settings.openai_timeout,
                    max_retries=settings.openai_max_retries
                )
                
                # Initialize validation and correction agents
                from agents.validation_agent import FeedbackValidatorAgent
                from agents.correction_agent import FeedbackCorrectionAgent
                
                validator_agent = FeedbackValidatorAgent(
                    model_name=settings.openai_model,  # Can use different model for validation
                    temperature=0.0,  # Strict validation
                    api_key=settings.api_key,
                    timeout=settings.openai_timeout,
                    max_retries=settings.openai_max_retries
                )
                
                correction_agent = FeedbackCorrectionAgent(
                    model_name=settings.openai_model,  # Can use different model for correction
                    temperature=0.3,  # Balanced creativity for corrections
                    api_key=settings.api_key,
                    timeout=settings.openai_timeout,
                    max_retries=settings.openai_max_retries
                )
                
                # Initialize services
                cv_service = CVService(cv_parser)
                feedback_service = FeedbackService(
                    feedback_agent,
                    validator_agent=validator_agent,
                    correction_agent=correction_agent,
                    max_validation_iterations=3
                )
                
                # Parse CV (only for rejected candidates)
                logger.info(f"[Background] Processing CV for feedback generation: {filename}")
                cv_data = cv_service.process_cv_from_pdf(str(filepath), verbose=False, candidate_id=candidate_id)
                
                # Get job offer from candidate's position in database
                from models.job_models import JobOffer
                candidate = get_candidate_by_id(candidate_id)
                if candidate and candidate.position_id:
                    position = get_position_by_id(candidate.position_id)
                    if position:
                        job_offer = JobOffer(
                            title=position.title,
                            company=position.company,
                            location="",
                            description=position.description or ""
                        )
                        logger.info(f"[Background] Using job offer from database: {job_offer.title} at {job_offer.company}")
                    else:
                        logger.warning(f"[Background] Position ID {candidate.position_id} not found in database")
                        job_offer = JobOffer(
                            title="Position",
                            company="",
                            location="",
                            description=""
                        )
                else:
                    logger.warning(f"[Background] Candidate {candidate_id} has no position_id assigned")
                    job_offer = JobOffer(
                        title="Position",
                        company="",
                        location="",
                        description=""
                    )
                
                # Get all HR notes for this candidate (including the one just saved)
                hr_notes_list = get_hr_notes_for_candidate(candidate_id)
                
                # Combine all HR notes into a single notes string for AI
                all_notes = []
                if hr_notes_list:
                    for note in hr_notes_list:
                        stage_name = note.stage.value if isinstance(note.stage, RecruitmentStage) else note.stage
                        stage_display = {
                            'initial_screening': 'Pierwsza selekcja',
                            'hr_interview': 'Rozmowa HR',
                            'technical_assessment': 'Weryfikacja wiedzy',
                            'final_interview': 'Rozmowa końcowa',
                            'offer': 'Oferta'
                        }.get(stage_name, stage_name)
                        note_date = note.created_at.strftime('%Y-%m-%d %H:%M') if note.created_at else 'N/A'
                        all_notes.append(f"[{stage_display} - {note_date}]\n{note.notes}")
                
                # Combine all notes for feedback generation
                combined_notes = "\n\n---\n\n".join(all_notes) if all_notes else notes
                
                # Create HR feedback for AI
                hr_feedback = HRFeedback(
                    decision=Decision.REJECTED,
                    notes=combined_notes,
                    position_applied=job_offer.title if job_offer else "Position",
                    interviewer_name="HR Team"
                )
                
                # Format recruitment stage for feedback generation
                stage_display = {
                    'initial_screening': 'Pierwsza selekcja',
                    'hr_interview': 'Rozmowa HR',
                    'technical_assessment': 'Weryfikacja wiedzy',
                    'final_interview': 'Rozmowa końcowa',
                    'offer': 'Oferta'
                }.get(current_stage.value, current_stage.value)
                
                # Generate feedback
                logger.info(f"[Background] Generating feedback for rejected candidate ID: {candidate_id} at stage: {stage_display}")
                candidate_feedback, is_validated, validation_error_info = feedback_service.generate_feedback(
                    cv_data,
                    hr_feedback,
                    job_offer=job_offer,
                    output_format=FeedbackFormat.HTML,
                    save_to_file=False,
                    candidate_id=candidate_id,
                    recruitment_stage=stage_display
                )
                
                # Check if validation failed
                if not is_validated and validation_error_info:
                    # Save validation error to database
                    logger.error(f"[Background] Validation failed for candidate {candidate_id}. Saving error to database.")
                    
                    # Get model responses for this candidate to include in error
                    from database.models import get_model_responses_for_candidate, save_validation_error
                    model_responses = get_model_responses_for_candidate(candidate_id)
                    
                    # Create summary of model responses
                    model_responses_summary = []
                    for resp in model_responses:
                        model_responses_summary.append({
                            'agent_type': resp.agent_type,
                            'model_name': resp.model_name,
                            'created_at': resp.created_at.isoformat() if resp.created_at else None
                        })
                    
                    # Create detailed error message with validation and correction numbers
                    total_validations = validation_error_info.get('total_validations', len(validation_error_info.get('validation_results', [])))
                    total_corrections = validation_error_info.get('total_corrections', 0)
                    last_validation = validation_error_info.get('last_validation_number', total_validations)
                    last_correction = validation_error_info.get('last_correction_number', total_corrections)
                    
                    error_message = (
                        f"Validation failed after {feedback_service.max_iterations} iterations. "
                        f"Feedback was not approved by validator. "
                        f"Total validations performed: {total_validations}, "
                        f"Total corrections performed: {total_corrections}, "
                        f"Last validation number: {last_validation}, "
                        f"Last correction number: {last_correction}"
                    )
                    
                    # Save error to database
                    save_validation_error(
                        candidate_id=candidate_id,
                        error_message=error_message,
                        feedback_html_content=candidate_feedback.html_content,
                        validation_results=json.dumps(validation_error_info.get('validation_results', []), ensure_ascii=False, indent=2),
                        model_responses_summary=json.dumps(model_responses_summary, ensure_ascii=False, indent=2)
                    )
                    
                    logger.error(f"[Background] Validation error saved for candidate {candidate_id}. Email will NOT be sent.")
                    return  # Exit without sending email
                
                # Get candidate again to get consent value
                candidate = get_candidate_by_id(candidate_id)
                consent_value = getattr(candidate, 'consent_for_other_positions', None) if candidate else None
                
                # Get HTML content with consent information
                html_content = feedback_service.get_feedback_html(candidate_feedback, consent_for_other_positions=consent_value)
                
                # If rejected and email provided, send email first to get Message-ID
                message_id = None
                feedback_email_id = None
                if candidate_email:
                    subject = f"Odpowiedź na aplikację - {job_offer.title if job_offer else 'Stanowisko'}"
                    if not settings.email_username or not settings.email_password:
                        logger.warning(f"[Background] Email not sent - Email credentials not configured for candidate {candidate_id}")
                    else:
                        success, message_id = send_email_gmail(candidate_email, subject, html_content)
                        if success:
                            logger.info(f"[Background] Email sent successfully to {candidate_email} for candidate {candidate_id} with Message-ID: {message_id}")
                        else:
                            logger.error(f"[Background] Failed to send email to {candidate_email} for candidate {candidate_id}")
                
                # Save feedback email to database with Message-ID
                try:
                    feedback_email = save_feedback_email(candidate_id, html_content, message_id=message_id)
                    feedback_email_id = feedback_email.id
                    logger.info(f"[Background] Feedback email saved to database for candidate {candidate_id} with Message-ID: {message_id}")
                except Exception as e:
                    logger.error(f"[Background] Could not save feedback email: {str(e)}", exc_info=True)
                
                logger.info(f"[Background] Feedback processing completed for candidate {candidate_id}")
                
            except Exception as e:
                logger.error(f"[Background] Error processing CV and generating feedback for candidate {candidate_id}: {str(e)}", exc_info=True)
        
        # Start background thread
        thread = threading.Thread(target=process_feedback_background, daemon=True)
        thread.start()
        
        # Return immediately with success message
        flash('Kandydat został odrzucony. Generowanie feedbacku i wysyłanie emaila odbywa się w tle. Sprawdź logi lub historię emaili, aby zobaczyć status.', 'success')
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))


@app.route('/admin')
def admin_panel():
    """Admin panel showing all database data."""
    try:
        # Get all data from database
        candidates = get_all_candidates()
        positions = get_all_positions()
        feedback_emails = get_all_feedback_emails()
        hr_notes = get_all_hr_notes()
        model_responses = get_all_model_responses()
        tickets = get_all_tickets()
        
        # Get position names for candidates
        position_dict = {pos.id: pos for pos in positions}
        for candidate in candidates:
            if candidate.position_id and candidate.position_id in position_dict:
                candidate.position_name = position_dict[candidate.position_id].title
            else:
                candidate.position_name = "Brak stanowiska"
        
        # Get candidate names for feedback emails
        candidate_dict = {cand.id: cand for cand in candidates}
        for email in feedback_emails:
            if email.candidate_id in candidate_dict:
                email.candidate_name = candidate_dict[email.candidate_id].full_name
                email.candidate_email = candidate_dict[email.candidate_id].email
            else:
                email.candidate_name = "Nieznany kandydat"
                email.candidate_email = "N/A"
        
        # Get candidate names for HR notes and ensure stage is accessible
        for note in hr_notes:
            if note.candidate_id in candidate_dict:
                note.candidate_name = candidate_dict[note.candidate_id].full_name
            else:
                note.candidate_name = "Nieznany kandydat"
            # Ensure stage is a string value for template
            if hasattr(note.stage, 'value'):
                note.stage_value = note.stage.value
            else:
                note.stage_value = str(note.stage) if note.stage else 'unknown'
        
        # Get candidate names and parse metadata for model responses
        for response in model_responses:
            if response.candidate_id and response.candidate_id in candidate_dict:
                response.candidate_name = candidate_dict[response.candidate_id].full_name
            else:
                response.candidate_name = "Nieznany kandydat"
            
            # Parse metadata to extract validation_number or correction_number
            response.validation_number = None
            response.correction_number = None
            if response.metadata:
                try:
                    import json
                    metadata = json.loads(response.metadata) if isinstance(response.metadata, str) else response.metadata
                    response.validation_number = metadata.get('validation_number')
                    response.correction_number = metadata.get('correction_number')
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return render_template('admin.html', 
                            candidates=candidates,
                            positions=positions,
                            feedback_emails=feedback_emails,
                            hr_notes=hr_notes,
                            model_responses=model_responses,
                            tickets=tickets)
    except Exception as e:
        logger.error(f"Error loading admin panel: {str(e)}", exc_info=True)
        flash(f'Błąd podczas ładowania panelu admina: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/metrics')
def metrics_dashboard():
    """Metrics dashboard showing system performance and health metrics."""
    try:
        days = request.args.get('days', 30, type=int)
        if days < 1 or days > 365:
            days = 30
        
        all_metrics = metrics_service.get_all_metrics(days=days)
        
        return render_template('metrics.html', metrics=all_metrics, days=days)
    except Exception as e:
        logger.error(f"Error loading metrics dashboard: {str(e)}", exc_info=True)
        flash(f'Błąd podczas ładowania metryk: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/db-view')
def db_view():
    """Simple database viewer showing all tables and data."""
    try:
        from database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get data from each table
        table_data = {}
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            table_data[table] = {
                'columns': columns,
                'rows': [dict(row) for row in rows],
                'count': len(rows)
            }
        
        conn.close()
        
        return render_template('db_view.html', tables=tables, table_data=table_data)
    except Exception as e:
        logger.error(f"Error loading database view: {str(e)}", exc_info=True)
        flash(f'Błąd podczas ładowania widoku bazy danych: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/db-export')
def db_export():
    """Export all database data as JSON."""
    try:
        from database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get data from each table
        export_data = {
            'export_date': datetime.now().isoformat(),
            'tables': {}
        }
        
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            export_data['tables'][table] = {
                'columns': columns,
                'rows': []
            }
            
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert datetime objects to strings
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    row_dict[col] = value
                export_data['tables'][table]['rows'].append(row_dict)
        
        conn.close()
        
        # Return as JSON download
        response = Response(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=db_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'}
        )
        return response
    except Exception as e:
        logger.error(f"Error exporting database: {str(e)}", exc_info=True)
        flash(f'Błąd podczas eksportu bazy danych: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/health')
def health():
    """Health check endpoint for Docker/Kubernetes."""
    try:
        # Check if database is working
        from database.models import get_db
        db = get_db()
        db.execute('SELECT 1').fetchone()
        return {'status': 'healthy', 'service': 'recruitment-ai'}, 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {'status': 'unhealthy', 'error': str(e)}, 503


if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, host='0.0.0.0', port=5000)


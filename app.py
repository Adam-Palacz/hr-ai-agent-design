"""Simple web application for HR to review CVs and send feedback emails."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from config import settings
from config.job_config import load_job_config, create_job_offer_from_config
from core.logger import logger, setup_logger
from agents.cv_parser_agent import CVParserAgent
from agents.feedback_agent import FeedbackAgent
from services.cv_service import CVService
from services.feedback_service import FeedbackService
from models.feedback_models import HRFeedback, Decision, FeedbackFormat
from database.models import (
    init_db, get_all_candidates, get_candidate_by_id, create_candidate,
    update_candidate, save_feedback_email, get_feedback_emails_for_candidate,
    get_all_feedback_emails, CandidateStatus, RecruitmentStage, 
    get_all_positions, create_position, get_position_by_id, update_position, delete_position,
    HRNote, create_hr_note, get_hr_notes_for_candidate, get_all_hr_notes
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

# Gmail SMTP configuration (reload after dotenv)
GMAIL_USERNAME = os.getenv('GMAIL_USERNAME', '')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD', '')  # App password for Gmail
GMAIL_CONFIG_PATH = os.getenv('GMAIL_CONFIG_PATH', 'config/job_config_example.yaml')

# Check Gmail configuration on startup
if not GMAIL_USERNAME or not GMAIL_PASSWORD:
    logger.warning(
        "Gmail credentials not configured. Email sending will be disabled.\n"
        "To enable email sending, add to .env file:\n"
        "  GMAIL_USERNAME=your-email@gmail.com\n"
        "  GMAIL_PASSWORD=your-app-password\n"
        "Get app password from: https://myaccount.google.com/apppasswords"
    )
else:
    logger.info(f"Gmail configured for: {GMAIL_USERNAME}")


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


def send_email_gmail(to_email: str, subject: str, html_content: str) -> bool:
    """
    Send email using Gmail SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not GMAIL_USERNAME or not GMAIL_PASSWORD:
        logger.error("Gmail credentials not configured. Set GMAIL_USERNAME and GMAIL_PASSWORD in .env")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = GMAIL_USERNAME
        msg['To'] = to_email
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Send email via Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USERNAME, GMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email} via Gmail")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


@app.route('/')
def index():
    """Main page with list of candidates."""
    candidates = get_all_candidates()
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
    
    # Create job offer from candidate's position
    job_offer = None
    if candidate.position_id:
        # Try to load from config first
        try:
            config = load_job_config(GMAIL_CONFIG_PATH)
            job_offer = create_job_offer_from_config(config)
        except Exception as e:
            logger.warning(f"Could not load job config: {str(e)}")
            # Create from candidate position info
            from models.job_models import JobOffer
            job_offer = JobOffer(
                title=getattr(candidate, 'position_title', ''),
                company=getattr(candidate, 'position_company', ''),
                location="",
                description=getattr(candidate, 'position_description', '')
            )
    
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
        consent_bool = None
        if consent_value == '1':
            consent_bool = True
        elif consent_value == '0':
            consent_bool = False
        # If empty string, leave as None
        
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
        consent_bool = None
        if consent_value == '1':
            consent_bool = True
        elif consent_value == '0':
            consent_bool = False
        # If empty string, leave as None
        
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
        # REJECTED: Generate feedback and send email
        # Only now we need to parse CV and generate feedback
        
        filepath = Path(candidate.cv_path) if candidate.cv_path else UPLOAD_FOLDER / filename
        if not filepath.exists():
            flash('Plik nie został znaleziony', 'error')
            return redirect(url_for('candidate_detail', candidate_id=candidate_id))
        
        try:
            # Initialize agents (only for rejected candidates)
            logger.info("Initializing agents for feedback generation...")
            cv_parser = CVParserAgent(
                model_name=settings.openai_model,
                vision_model_name=settings.openai_vision_model,
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
            
            # Initialize services
            cv_service = CVService(cv_parser)
            feedback_service = FeedbackService(feedback_agent)
            
            # Parse CV (only for rejected candidates)
            logger.info(f"Processing CV for feedback generation: {filename}")
            cv_data = cv_service.process_cv_from_pdf(str(filepath), verbose=False)
            
            # Try to load job offer from config
            from models.job_models import JobOffer
            try:
                config = load_job_config(GMAIL_CONFIG_PATH)
                job_offer = create_job_offer_from_config(config)
                logger.info(f"Using job offer from config: {job_offer.title} at {job_offer.company}")
            except Exception as e:
                logger.warning(f"Could not load job config: {str(e)}")
                # If config not available, try to get from candidate's position
                if candidate.position_id:
                    position = get_position_by_id(candidate.position_id)
                    if position:
                        job_offer = JobOffer(
                            title=position.title,
                            company=position.company,
                            location="",
                            description=position.description or ""
                        )
                    else:
                        job_offer = JobOffer(
                            title="Position",
                            company="",
                            location="",
                            description=""
                        )
                else:
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
            
            # Generate feedback
            logger.info(f"Generating feedback for rejected candidate: {cv_data.full_name}")
            candidate_feedback = feedback_service.generate_feedback(
                cv_data,
                hr_feedback,
                job_offer=job_offer,
                output_format=FeedbackFormat.HTML,
                save_to_file=False
            )
            
            # Get HTML content with consent information
            consent_value = getattr(candidate, 'consent_for_other_positions', None)
            html_content = feedback_service.get_feedback_html(candidate_feedback, consent_for_other_positions=consent_value)
            
            # Update candidate status to REJECTED
            try:
                update_candidate(
                    candidate_id,
                    status=CandidateStatus.REJECTED.value,
                    stage=current_stage.value
                )
                logger.info(f"Updated candidate {candidate_id}: status=rejected, stage={current_stage.value}")
            except Exception as e:
                logger.warning(f"Could not update candidate status/stage: {str(e)}")
            
            # Save feedback email to database
            try:
                save_feedback_email(candidate_id, html_content)
            except Exception as e:
                logger.warning(f"Could not save feedback email: {str(e)}")
            
            # If rejected and email provided, send email
            email_sent = False
            if candidate_email:
                subject = f"Odpowiedź na aplikację - {job_offer.title if job_offer else 'Stanowisko'}"
                if not GMAIL_USERNAME or not GMAIL_PASSWORD:
                    flash(
                        'Email nie został wysłany - brak konfiguracji Gmail. '
                        'Dodaj GMAIL_USERNAME i GMAIL_PASSWORD do pliku .env',
                        'error'
                    )
                elif send_email_gmail(candidate_email, subject, html_content):
                    flash(f'Email został wysłany do {candidate_email}', 'success')
                    email_sent = True
                else:
                    flash(
                        'Błąd podczas wysyłania emaila. Sprawdź konfigurację Gmail '
                        '(GMAIL_USERNAME i GMAIL_PASSWORD w .env)',
                        'error'
                    )
            
            # Save feedback email to database (always save, even if email not sent)
            try:
                save_feedback_email(candidate_id, html_content)
            except Exception as e:
                logger.warning(f"Could not save feedback email: {str(e)}")
            
            return redirect(url_for('candidate_detail', candidate_id=candidate_id))
        
        except Exception as e:
            logger.error(f"Error processing CV and generating feedback: {str(e)}", exc_info=True)
            flash(f'Błąd podczas przetwarzania CV i generowania feedbacku: {str(e)}', 'error')
            return redirect(url_for('candidate_detail', candidate_id=candidate_id))


@app.route('/admin')
def admin_panel():
    """Admin panel showing all database data."""
    try:
        # Get all data from database
        candidates = get_all_candidates()
        positions = get_all_positions()
        feedback_emails = get_all_feedback_emails()
        
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
        
        return render_template('admin.html', 
                            candidates=candidates,
                            positions=positions,
                            feedback_emails=feedback_emails)
    except Exception as e:
        logger.error(f"Error loading admin panel: {str(e)}", exc_info=True)
        flash(f'Błąd podczas ładowania panelu admina: {str(e)}', 'error')
        return redirect(url_for('index'))


if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, host='0.0.0.0', port=5000)


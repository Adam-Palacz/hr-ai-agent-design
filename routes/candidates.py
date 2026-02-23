"""Candidate and upload routes."""

from pathlib import Path
from flask import request, redirect, url_for, flash, render_template, send_from_directory
from werkzeug.utils import secure_filename

from database.models import (
    get_all_candidates,
    get_candidate_by_id,
    create_candidate,
    update_candidate,
    get_feedback_emails_for_candidate,
    get_hr_notes_for_candidate,
    get_all_positions,
    get_position_by_id,
    delete_candidate,
)
from routes.helpers import allowed_file
from core.logger import logger


def register_candidates(app):
    """Register candidate-related routes."""

    @app.route("/")
    def index():
        """Main page with list of candidates."""
        candidates = get_all_candidates()
        positions = get_all_positions()
        position_dict = {pos.id: pos for pos in positions}
        for candidate in candidates:
            if candidate.position_id and candidate.position_id in position_dict:
                position = position_dict[candidate.position_id]
                candidate.position_title = position.title
                candidate.position_company = position.company
            else:
                candidate.position_title = None
                candidate.position_company = None
        return render_template("candidates_list.html", candidates=candidates)

    @app.route("/upload", methods=["POST"])
    def upload_file():
        """Handle PDF upload."""
        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        allowed_extensions = app.config["ALLOWED_EXTENSIONS"]
        if "pdf_file" not in request.files:
            flash("Brak pliku PDF", "error")
            return redirect(url_for("index"))
        file = request.files["pdf_file"]
        if file.filename == "":
            flash("Nie wybrano pliku", "error")
            return redirect(url_for("index"))
        if file and allowed_file(file.filename, allowed_extensions):
            filename = secure_filename(file.filename)
            filepath = upload_folder / filename
            file.save(str(filepath))
            logger.info(f"PDF uploaded: {filename}")
            return redirect(url_for("index"))
        flash("Nieprawidłowy format pliku. Dozwolone tylko PDF.", "error")
        return redirect(url_for("index"))

    @app.route("/candidate/<int:candidate_id>")
    def candidate_detail(candidate_id):
        """Candidate detail page with PDF viewer and feedback form."""
        candidate = get_candidate_by_id(candidate_id)
        if not candidate:
            flash("Kandydat nie został znaleziony", "error")
            return redirect(url_for("index"))
        if not candidate.cv_path:
            flash("Brak pliku CV dla tego kandydata", "error")
            return redirect(url_for("index"))
        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        filepath = Path(candidate.cv_path)
        if not filepath.exists():
            flash("Plik CV nie został znaleziony", "error")
            return redirect(url_for("index"))
        try:
            filename = filepath.relative_to(upload_folder).as_posix()
        except ValueError:
            filename = filepath.name
            if not (upload_folder / filename).exists():
                import shutil

                shutil.copy2(str(filepath), str(upload_folder / filename))
        feedback_emails = get_feedback_emails_for_candidate(candidate_id)
        job_offer = None
        if candidate.position_id:
            position = get_position_by_id(candidate.position_id)
            if position:
                from models.job_models import JobOffer

                job_offer = JobOffer(
                    title=position.title,
                    company=position.company,
                    location="",
                    description=position.description or "",
                )
                logger.info(
                    f"Loaded job offer from database: {job_offer.title} at {job_offer.company}"
                )
            else:
                logger.warning(f"Position ID {candidate.position_id} not found in database")
        hr_notes = get_hr_notes_for_candidate(candidate_id)
        return render_template(
            "review.html",
            candidate=candidate,
            filename=filename,
            job_offer=job_offer,
            feedback_emails=feedback_emails,
            hr_notes=hr_notes,
        )

    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        """Serve uploaded PDF files."""
        upload_folder = app.config["UPLOAD_FOLDER"]
        filepath = Path(upload_folder) / filename
        if filepath.exists():
            return send_from_directory(str(upload_folder), filename)
        return send_from_directory(str(upload_folder), filename)

    @app.route("/add_candidate", methods=["GET", "POST"])
    def add_candidate():
        """Add a new candidate."""
        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        allowed_extensions = app.config["ALLOWED_EXTENSIONS"]
        if request.method == "POST":
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            email = request.form.get("email", "").strip()
            position_id = request.form.get("position_id", "").strip()
            cv_file = request.files.get("cv_file")
            if not first_name or not last_name or not email:
                flash("Wypełnij wszystkie wymagane pola", "error")
                return redirect(url_for("add_candidate"))
            cv_path = None
            if cv_file and cv_file.filename and allowed_file(cv_file.filename, allowed_extensions):
                filename = secure_filename(cv_file.filename)
                filepath = upload_folder / filename
                filepath.parent.mkdir(exist_ok=True)
                cv_file.save(str(filepath))
                cv_path = str(filepath)
            consent_value = request.form.get("consent_for_other_positions", "").strip()
            if consent_value not in ("1", "0"):
                flash("Wybierz zgodę na rozważenie do innych stanowisk (Tak/Nie)", "error")
                return redirect(url_for("add_candidate"))
            consent_bool = consent_value == "1"
            position_id_int = int(position_id) if position_id else None
            create_candidate(
                first_name=first_name,
                last_name=last_name,
                email=email,
                position_id=position_id_int,
                cv_path=cv_path,
                consent_for_other_positions=consent_bool,
            )
            flash("Kandydat został dodany", "success")
            return redirect(url_for("index"))
        positions = get_all_positions()
        return render_template("add_candidate.html", positions=positions)

    @app.route("/candidate/<int:candidate_id>/edit", methods=["GET", "POST"])
    def edit_candidate(candidate_id):
        """Edit candidate information."""
        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        allowed_extensions = app.config["ALLOWED_EXTENSIONS"]
        candidate = get_candidate_by_id(candidate_id)
        if not candidate:
            flash("Kandydat nie został znaleziony", "error")
            return redirect(url_for("index"))
        if request.method == "POST":
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            email = request.form.get("email", "").strip()
            position_id = request.form.get("position_id", "").strip()
            cv_file = request.files.get("cv_file")
            if not first_name or not last_name or not email:
                flash("Wypełnij wszystkie wymagane pola", "error")
                return redirect(url_for("edit_candidate", candidate_id=candidate_id))
            cv_path = candidate.cv_path
            if cv_file and cv_file.filename and allowed_file(cv_file.filename, allowed_extensions):
                filename = secure_filename(cv_file.filename)
                filepath = upload_folder / filename
                filepath.parent.mkdir(exist_ok=True)
                cv_file.save(str(filepath))
                cv_path = str(filepath)
            position_id_int = int(position_id) if position_id else None
            consent_value = request.form.get("consent_for_other_positions", "").strip()
            if consent_value not in ("1", "0"):
                flash("Wybierz zgodę na rozważenie do innych stanowisk (Tak/Nie)", "error")
                return redirect(url_for("edit_candidate", candidate_id=candidate_id))
            consent_bool = consent_value == "1"
            update_candidate(
                candidate_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                position_id=position_id_int,
                cv_path=cv_path,
                consent_for_other_positions=consent_bool,
            )
            flash("Kandydat został zaktualizowany", "success")
            return redirect(url_for("candidate_detail", candidate_id=candidate_id))
        positions = get_all_positions()
        return render_template("edit_candidate.html", candidate=candidate, positions=positions)

    @app.route("/candidate/<int:candidate_id>/delete", methods=["POST"])
    def delete_candidate_route(candidate_id):
        """Delete a candidate."""
        if delete_candidate(candidate_id):
            flash("Kandydat został usunięty", "success")
        else:
            flash("Nie można usunąć kandydata", "error")
        return redirect(url_for("index"))

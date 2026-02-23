"""Admin, metrics, db-view and db-export routes."""

import json
from datetime import datetime
from flask import request, redirect, url_for, flash, render_template, Response

from core.logger import logger
from database.models import (
    get_all_candidates,
    get_all_positions,
    get_all_feedback_emails,
    get_all_hr_notes,
    get_all_model_responses,
    get_all_tickets,
    get_db,
)
from services.metrics_service import metrics_service


def register_admin(app):
    """Register admin and metrics routes."""

    @app.route("/admin")
    def admin_panel():
        """Admin panel showing all database data."""
        try:
            candidates = get_all_candidates()
            positions = get_all_positions()
            feedback_emails = get_all_feedback_emails()
            hr_notes = get_all_hr_notes()
            model_responses = get_all_model_responses()
            tickets = get_all_tickets()

            position_dict = {pos.id: pos for pos in positions}
            for candidate in candidates:
                if candidate.position_id and candidate.position_id in position_dict:
                    candidate.position_name = position_dict[candidate.position_id].title
                else:
                    candidate.position_name = "Brak stanowiska"

            candidate_dict = {cand.id: cand for cand in candidates}
            for email in feedback_emails:
                if email.candidate_id in candidate_dict:
                    email.candidate_name = candidate_dict[email.candidate_id].full_name
                    email.candidate_email = candidate_dict[email.candidate_id].email
                else:
                    email.candidate_name = "Nieznany kandydat"
                    email.candidate_email = "N/A"

            for note in hr_notes:
                if note.candidate_id in candidate_dict:
                    note.candidate_name = candidate_dict[note.candidate_id].full_name
                else:
                    note.candidate_name = "Nieznany kandydat"
                note.stage_value = (
                    note.stage.value
                    if hasattr(note.stage, "value")
                    else str(note.stage) if note.stage else "unknown"
                )

            for response in model_responses:
                if response.candidate_id and response.candidate_id in candidate_dict:
                    response.candidate_name = candidate_dict[response.candidate_id].full_name
                else:
                    response.candidate_name = "Nieznany kandydat"
                response.validation_number = None
                response.correction_number = None
                if response.metadata:
                    try:
                        metadata = (
                            json.loads(response.metadata)
                            if isinstance(response.metadata, str)
                            else response.metadata
                        )
                        response.validation_number = metadata.get("validation_number")
                        response.correction_number = metadata.get("correction_number")
                    except (json.JSONDecodeError, TypeError):
                        pass

            return render_template(
                "admin.html",
                candidates=candidates,
                positions=positions,
                feedback_emails=feedback_emails,
                hr_notes=hr_notes,
                model_responses=model_responses,
                tickets=tickets,
            )
        except Exception as e:
            logger.error(f"Error loading admin panel: {str(e)}", exc_info=True)
            flash(f"Błąd podczas ładowania panelu admina: {str(e)}", "error")
            return redirect(url_for("index"))

    @app.route("/metrics")
    def metrics_dashboard():
        """Metrics dashboard showing system performance and health metrics."""
        try:
            days = request.args.get("days", 30, type=int)
            if days < 1 or days > 365:
                days = 30
            all_metrics = metrics_service.get_all_metrics(days=days)
            return render_template("metrics.html", metrics=all_metrics, days=days)
        except Exception as e:
            logger.error(f"Error loading metrics dashboard: {str(e)}", exc_info=True)
            flash(f"Błąd podczas ładowania metryk: {str(e)}", "error")
            return redirect(url_for("index"))

    @app.route("/db-view")
    def db_view():
        """Simple database viewer showing all tables and data."""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            table_data = {}
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                table_data[table] = {
                    "columns": columns,
                    "rows": [dict(row) for row in rows],
                    "count": len(rows),
                }
            conn.close()
            return render_template("db_view.html", tables=tables, table_data=table_data)
        except Exception as e:
            logger.error(f"Error loading database view: {str(e)}", exc_info=True)
            flash(f"Błąd podczas ładowania widoku bazy danych: {str(e)}", "error")
            return redirect(url_for("index"))

    @app.route("/db-export")
    def db_export():
        """Export all database data as JSON."""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            export_data = {"export_date": datetime.now().isoformat(), "tables": {}}
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                export_data["tables"][table] = {"columns": columns, "rows": []}
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        row_dict[col] = value
                    export_data["tables"][table]["rows"].append(row_dict)
            conn.close()
            response = Response(
                json.dumps(export_data, indent=2, ensure_ascii=False),
                mimetype="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename=db_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                },
            )
            return response
        except Exception as e:
            logger.error(f"Error exporting database: {str(e)}", exc_info=True)
            flash(f"Błąd podczas eksportu bazy danych: {str(e)}", "error")
            return redirect(url_for("index"))

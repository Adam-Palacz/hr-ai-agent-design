"""Position routes."""

from flask import request, redirect, url_for, flash, render_template

from database.models import (
    get_all_positions,
    get_position_by_id,
    create_position,
    update_position,
    delete_position,
)


def register_positions(app):
    """Register position-related routes."""

    @app.route("/positions")
    def positions_list():
        """List all positions."""
        positions = get_all_positions()
        return render_template("positions_list.html", positions=positions)

    @app.route("/positions/add", methods=["GET", "POST"])
    def add_position():
        """Add a new position."""
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            company = request.form.get("company", "").strip()
            description = request.form.get("description", "").strip()
            if not title or not company:
                flash("Wypełnij wszystkie wymagane pola", "error")
                return redirect(url_for("add_position"))
            create_position(title=title, company=company, description=description)
            flash("Pozycja została dodana", "success")
            return redirect(url_for("positions_list"))
        return render_template("add_position.html")

    @app.route("/positions/<int:position_id>/edit", methods=["GET", "POST"])
    def edit_position(position_id):
        """Edit a position."""
        position = get_position_by_id(position_id)
        if not position:
            flash("Pozycja nie została znaleziona", "error")
            return redirect(url_for("positions_list"))
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            company = request.form.get("company", "").strip()
            description = request.form.get("description", "").strip()
            if not title or not company:
                flash("Wypełnij wszystkie wymagane pola", "error")
                return redirect(url_for("edit_position", position_id=position_id))
            update_position(position_id, title=title, company=company, description=description)
            flash("Pozycja została zaktualizowana", "success")
            return redirect(url_for("positions_list"))
        return render_template("edit_position.html", position=position)

    @app.route("/positions/<int:position_id>/delete", methods=["POST"])
    def delete_position_route(position_id):
        """Delete a position."""
        if delete_position(position_id):
            flash("Pozycja została usunięta", "success")
        else:
            flash("Nie można usunąć pozycji", "error")
        return redirect(url_for("positions_list"))

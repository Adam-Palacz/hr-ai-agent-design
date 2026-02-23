"""Ticket routes."""

from datetime import datetime
from flask import request, redirect, url_for, flash, render_template

from database.models import (
    get_all_tickets,
    get_ticket_by_id,
    create_ticket,
    update_ticket,
    delete_ticket,
    get_all_candidates,
)
from database.schema import TicketDepartment, TicketPriority, TicketStatus


def register_tickets(app):
    """Register ticket-related routes."""

    @app.route("/tickets")
    def tickets_list():
        """List all tickets."""
        tickets = get_all_tickets()
        candidates_dict = {c.id: c for c in get_all_candidates()}
        for ticket in tickets:
            if ticket.related_candidate_id and ticket.related_candidate_id in candidates_dict:
                ticket.candidate = candidates_dict[ticket.related_candidate_id]
            else:
                ticket.candidate = None
        return render_template("tickets_list.html", tickets=tickets)

    @app.route("/tickets/add", methods=["GET", "POST"])
    def add_ticket():
        """Add a new ticket."""
        if request.method == "POST":
            department = request.form.get("department", "").strip()
            priority = request.form.get("priority", "").strip()
            status = request.form.get("status", "").strip()
            description = request.form.get("description", "").strip()
            deadline_str = request.form.get("deadline", "").strip()
            if not department or not priority or not description:
                flash("Wypełnij wszystkie wymagane pola", "error")
                return redirect(url_for("add_ticket"))
            deadline = None
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace("T", " "))
                except ValueError:
                    flash("Nieprawidłowy format daty deadline", "error")
                    return redirect(url_for("add_ticket"))
            create_ticket(
                department=TicketDepartment(department),
                priority=TicketPriority(priority),
                status=TicketStatus(status) if status else TicketStatus.OPEN,
                description=description,
                deadline=deadline,
            )
            flash("Ticket został utworzony", "success")
            return redirect(url_for("tickets_list"))
        return render_template("add_ticket.html")

    @app.route("/tickets/<int:ticket_id>/edit", methods=["GET", "POST"])
    def edit_ticket(ticket_id):
        """Edit a ticket."""
        ticket = get_ticket_by_id(ticket_id)
        if not ticket:
            flash("Ticket nie został znaleziony", "error")
            return redirect(url_for("tickets_list"))
        if request.method == "POST":
            department = request.form.get("department", "").strip()
            priority = request.form.get("priority", "").strip()
            status = request.form.get("status", "").strip()
            description = request.form.get("description", "").strip()
            deadline_str = request.form.get("deadline", "").strip()
            if not department or not priority or not description:
                flash("Wypełnij wszystkie wymagane pola", "error")
                return redirect(url_for("edit_ticket", ticket_id=ticket_id))
            deadline = None
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace("T", " "))
                except ValueError:
                    flash("Nieprawidłowy format daty deadline", "error")
                    return redirect(url_for("edit_ticket", ticket_id=ticket_id))
            update_ticket(
                ticket_id,
                department=TicketDepartment(department),
                priority=TicketPriority(priority),
                status=TicketStatus(status) if status else None,
                description=description,
                deadline=deadline,
            )
            flash("Ticket został zaktualizowany", "success")
            return redirect(url_for("tickets_list"))
        return render_template("edit_ticket.html", ticket=ticket)

    @app.route("/tickets/<int:ticket_id>/delete", methods=["POST"])
    def delete_ticket_route(ticket_id):
        """Delete a ticket."""
        if delete_ticket(ticket_id):
            flash("Ticket został usunięty", "success")
        else:
            flash("Nie można usunąć ticketu", "error")
        return redirect(url_for("tickets_list"))

"""Flask route registration."""

from routes.candidates import register_candidates
from routes.positions import register_positions
from routes.tickets import register_tickets
from routes.process import register_process
from routes.admin import register_admin
from routes.health import register_health


def register_all_routes(app):
    """Register all route modules on the Flask app."""
    register_candidates(app)
    register_positions(app)
    register_tickets(app)
    register_process(app)
    register_admin(app)
    register_health(app)

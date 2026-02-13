"""Health check route."""

from flask import jsonify

from core.logger import logger
from database.models import get_db


def register_health(app):
    """Register health check route."""

    @app.route("/health")
    def health():
        """Health check endpoint for Docker/Kubernetes."""
        try:
            db = get_db()
            db.execute("SELECT 1").fetchone()
            return jsonify({"status": "healthy", "service": "recruitment-ai"}), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({"status": "unhealthy", "error": str(e)}), 503

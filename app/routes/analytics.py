from flask import Blueprint, render_template

from app.services.analytics_service import get_dashboard_snapshot


analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
def dashboard():
    return render_template("analytics/dashboard.html", dashboard=get_dashboard_snapshot())

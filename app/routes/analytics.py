from flask import Blueprint, render_template

from app.services.analytics_service import get_dashboard_data


analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
def dashboard():
    dashboard_data = get_dashboard_data()
    return render_template("analytics/dashboard.html", dashboard=dashboard_data)

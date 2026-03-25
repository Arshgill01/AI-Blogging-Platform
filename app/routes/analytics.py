from flask import Blueprint, render_template


analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
def dashboard():
    return render_template("analytics/placeholder.html")

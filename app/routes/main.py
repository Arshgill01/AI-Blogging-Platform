from flask import Blueprint, redirect, render_template, url_for

from app.models import Post
from app.services.analytics_service import get_home_snapshot
from app.services.personalization_service import (
    ensure_reader_session,
    get_personalized_recommendations,
)


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    session_token = ensure_reader_session()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    personalized_recommendations = get_personalized_recommendations(session_token, limit=4)
    home_snapshot = get_home_snapshot()
    return render_template(
        "home.html",
        posts=posts,
        personalized_recommendations=personalized_recommendations,
        home_snapshot=home_snapshot,
    )


@main_bp.route("/dashboard")
def dashboard_shortcut():
    return redirect(url_for("analytics.dashboard"))


@main_bp.route("/author")
@main_bp.route("/studio")
def author_shortcut():
    return redirect(url_for("posts.create"))

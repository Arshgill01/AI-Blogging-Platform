from flask import Blueprint, render_template

from app.models import Post
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
    return render_template(
        "home.html",
        posts=posts,
        personalized_recommendations=personalized_recommendations,
    )

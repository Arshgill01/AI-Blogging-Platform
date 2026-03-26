from flask import Blueprint, render_template

from app.models import Post
from app.services.personalization_service import ensure_reader_session


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    ensure_reader_session()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("home.html", posts=posts)

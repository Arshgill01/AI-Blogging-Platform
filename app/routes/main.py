from flask import Blueprint, render_template

from app.models import Post


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("home.html", posts=posts)

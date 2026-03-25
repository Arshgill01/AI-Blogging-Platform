from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Post


posts_bp = Blueprint("posts", __name__, url_prefix="/posts")


@posts_bp.route("/<int:post_id>")
def detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("posts/detail.html", post=post)


@posts_bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        post = Post(
            title=request.form.get("title", "").strip(),
            content=request.form.get("content", "").strip(),
            category=request.form.get("category", "").strip() or "General",
            tags=request.form.get("tags", "").strip(),
            meta_description=request.form.get("meta_description", "").strip(),
        )

        if not post.title or not post.content:
            flash("Title and content are required.", "danger")
            return render_template("posts/form.html", post=post, form_title="Create Post")

        db.session.add(post)
        db.session.commit()
        flash("Post created.", "success")
        return redirect(url_for("posts.detail", post_id=post.id))

    return render_template("posts/form.html", post=None, form_title="Create Post")


@posts_bp.route("/<int:post_id>/edit", methods=["GET", "POST"])
def edit(post_id):
    post = Post.query.get_or_404(post_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            flash("Title and content are required.", "danger")
            return render_template("posts/form.html", post=post, form_title="Edit Post")

        post.title = title
        post.content = content
        post.category = request.form.get("category", "").strip() or "General"
        post.tags = request.form.get("tags", "").strip()
        post.meta_description = request.form.get("meta_description", "").strip()

        db.session.commit()
        flash("Post updated.", "success")
        return redirect(url_for("posts.detail", post_id=post.id))

    return render_template("posts/form.html", post=post, form_title="Edit Post")

from types import SimpleNamespace

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Post
from app.services.seo_service import (
    analyze_post_fields,
    get_latest_post_analysis,
    save_post_analysis,
)
from app.services.similarity_service import get_internal_link_suggestions, get_related_posts


posts_bp = Blueprint("posts", __name__, url_prefix="/posts")


def _post_form_state(source_post=None):
    if source_post is None:
        return SimpleNamespace(
            id=None,
            title="",
            content="",
            category="General",
            tags="",
            meta_description="",
        )

    return SimpleNamespace(
        id=getattr(source_post, "id", None),
        title=getattr(source_post, "title", "") or "",
        content=getattr(source_post, "content", "") or "",
        category=getattr(source_post, "category", "") or "General",
        tags=getattr(source_post, "tags", "") or "",
        meta_description=getattr(source_post, "meta_description", "") or "",
    )


def _populate_form_state(form_state):
    form_state.title = request.form.get("title", "").strip()
    form_state.content = request.form.get("content", "").strip()
    form_state.category = request.form.get("category", "").strip() or "General"
    form_state.tags = request.form.get("tags", "").strip()
    form_state.meta_description = request.form.get("meta_description", "").strip()
    return form_state


def _apply_form_to_post(post, form_state):
    post.title = form_state.title
    post.content = form_state.content
    post.category = form_state.category
    post.tags = form_state.tags
    post.meta_description = form_state.meta_description
    return post


def _build_author_similarity_context(post):
    if post is None or getattr(post, "id", None) is None:
        return []
    return get_internal_link_suggestions(post, limit=4)


def _render_post_form(form_title, post_form, analysis=None, internal_link_suggestions=None):
    return render_template(
        "posts/form.html",
        post=post_form,
        form_title=form_title,
        analysis=analysis,
        is_edit=bool(getattr(post_form, "id", None)),
        internal_link_suggestions=internal_link_suggestions or [],
    )


@posts_bp.route("/<int:post_id>")
def detail(post_id):
    post = db.get_or_404(Post, post_id)
    latest_analysis = get_latest_post_analysis(post)
    related_posts = get_related_posts(post, limit=3)
    internal_link_suggestions = (
        latest_analysis.get("internal_links")
        if latest_analysis and latest_analysis.get("internal_links")
        else get_internal_link_suggestions(post, limit=4)
    )
    return render_template(
        "posts/detail.html",
        post=post,
        latest_analysis=latest_analysis,
        related_posts=related_posts,
        internal_link_suggestions=internal_link_suggestions,
    )


@posts_bp.route("/<int:post_id>/analyze", methods=["POST"])
def analyze(post_id):
    post = db.get_or_404(Post, post_id)
    internal_link_suggestions = get_internal_link_suggestions(post, limit=4)
    analysis = analyze_post_fields(
        title=post.title,
        content=post.content,
        meta_description=post.meta_description,
        tags=post.tags,
        category=post.category,
    )
    save_post_analysis(post, analysis, internal_links=internal_link_suggestions)
    flash("SEO analysis refreshed for this post.", "success")
    return redirect(url_for("posts.detail", post_id=post.id))


@posts_bp.route("/new", methods=["GET", "POST"])
def create():
    post_form = _post_form_state()

    if request.method == "POST":
        action = request.form.get("action", "save")
        post_form = _populate_form_state(post_form)

        if not post_form.title or not post_form.content:
            flash("Title and content are required.", "danger")
            return _render_post_form("Create Post", post_form)

        post = _apply_form_to_post(Post(), post_form)
        db.session.add(post)
        db.session.commit()

        if action == "analyze":
            internal_link_suggestions = get_internal_link_suggestions(post, limit=4)
            analysis = analyze_post_fields(
                title=post.title,
                content=post.content,
                meta_description=post.meta_description,
                tags=post.tags,
                category=post.category,
            )
            save_post_analysis(post, analysis, internal_links=internal_link_suggestions)
            flash("Post created and SEO analysis generated.", "success")
            return redirect(url_for("posts.edit", post_id=post.id))

        flash("Post created.", "success")
        return redirect(url_for("posts.detail", post_id=post.id))

    return _render_post_form("Create Post", post_form)


@posts_bp.route("/<int:post_id>/edit", methods=["GET", "POST"])
def edit(post_id):
    post = db.get_or_404(Post, post_id)
    post_form = _post_form_state(post)
    internal_link_suggestions = _build_author_similarity_context(post)

    if request.method == "POST":
        action = request.form.get("action", "save")
        post_form = _populate_form_state(post_form)

        if not post_form.title or not post_form.content:
            flash("Title and content are required.", "danger")
            return _render_post_form(
                "Edit Post",
                post_form,
                analysis=get_latest_post_analysis(post),
                internal_link_suggestions=internal_link_suggestions,
            )

        _apply_form_to_post(post, post_form)
        db.session.commit()
        internal_link_suggestions = _build_author_similarity_context(post)

        if action == "analyze":
            analysis = analyze_post_fields(
                title=post.title,
                content=post.content,
                meta_description=post.meta_description,
                tags=post.tags,
                category=post.category,
            )
            save_post_analysis(post, analysis, internal_links=internal_link_suggestions)
            flash("Post updated and SEO analysis generated.", "success")
            return redirect(url_for("posts.edit", post_id=post.id))

        flash("Post updated.", "success")
        return redirect(url_for("posts.detail", post_id=post.id))

    return _render_post_form(
        "Edit Post",
        post_form,
        analysis=get_latest_post_analysis(post),
        internal_link_suggestions=internal_link_suggestions,
    )

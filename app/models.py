from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint

from app import db


def utcnow():
    return datetime.now(timezone.utc)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False, default="General")
    tags = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.String(320), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    seo_reports = db.relationship("SEOReport", back_populates="post", lazy=True)
    interactions = db.relationship("Interaction", back_populates="post", lazy=True)


class VisitorSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_token = db.Column(db.String(120), nullable=False, unique=True, index=True)
    first_seen = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    interactions = db.relationship("Interaction", back_populates="visitor_session", lazy=True)


class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_token = db.Column(
        db.String(120), db.ForeignKey("visitor_session.session_token"), nullable=False, index=True
    )
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    dwell_time = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    post = db.relationship("Post", back_populates="interactions")
    visitor_session = db.relationship("VisitorSession", back_populates="interactions")


class SEOReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
    word_count = db.Column(db.Integer, nullable=True)
    readability_score = db.Column(db.Float, nullable=True)
    seo_score = db.Column(db.Float, nullable=True)
    suggestions_json = db.Column(db.Text, nullable=True)
    keywords_json = db.Column(db.Text, nullable=True)
    internal_links_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    post = db.relationship("Post", back_populates="seo_reports")

    __table_args__ = (UniqueConstraint("post_id", "created_at", name="uq_seo_report_post_created"),)


def seed_demo_content():
    if Post.query.first():
        return

    demo_posts = [
        Post(
            title="Building a Self-Contained Content Engine",
            content=(
                "A strong blogging platform starts with a clean content model. "
                "This seed post exists so the homepage and detail pages have meaningful data "
                "before richer demo content is added in later waves."
            ),
            category="Platform",
            tags="architecture,content,mvp",
            meta_description="Why a self-contained content engine makes the MVP easier to extend.",
        ),
        Post(
            title="Why Explainable Features Matter in an MVP",
            content=(
                "Explainable ranking and analysis features are easier to debug, demo, and improve. "
                "For this project that means readable heuristics, traceable data models, and simple flows."
            ),
            category="Product",
            tags="mvp,seo,recommendations",
            meta_description="Simple, explainable product intelligence is the right tradeoff for this MVP.",
        ),
    ]

    db.session.add_all(demo_posts)
    db.session.commit()

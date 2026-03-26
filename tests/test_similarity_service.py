from types import SimpleNamespace

from app import create_app
from app.models import Post
from app.services.similarity_service import (
    build_post_document,
    get_related_posts,
    get_related_posts_for_fields,
)


def make_app():
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )


def test_build_post_document_weights_key_fields():
    document = build_post_document(
        title="SEO Basics",
        content="Useful content body",
        category="SEO",
        tags="meta descriptions, readability",
    )

    assert document.count("SEO Basics") == 3
    assert document.count("SEO") >= 2
    assert "meta descriptions readability" in document
    assert "Useful content body" in document


def test_get_related_posts_excludes_self_and_respects_limit():
    app = make_app()
    with app.app_context():
        post = Post.query.filter_by(title="Practical SEO Habits for Small Content Teams").first()

        related = get_related_posts(post, limit=3)

        assert len(related) == 3
        assert all(item["post_id"] != post.id for item in related)
        assert related[0]["similarity_score"] >= related[-1]["similarity_score"]


def test_get_related_posts_prefers_strong_cluster_matches():
    app = make_app()
    with app.app_context():
        post = Post.query.filter_by(title="Designing a Lightweight Flask Admin for Writers").first()

        related = get_related_posts(post, limit=3)

        assert related
        assert related[0]["title"] == "Useful Python Scripts for Cleaning Blog Metadata"
        assert "same-category" in related[0]["reason_codes"]


def test_get_related_posts_for_fields_handles_sparse_candidates():
    candidates = [
        SimpleNamespace(id=1, title="Empty", content="", category="SEO", tags="", created_at=None, updated_at=None),
    ]

    related = get_related_posts_for_fields(
        title="",
        content="",
        category="",
        tags="",
        candidate_posts=candidates,
    )

    assert related == []

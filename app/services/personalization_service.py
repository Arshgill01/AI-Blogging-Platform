from collections import defaultdict
from uuid import uuid4

from flask import session
from sqlalchemy import func

from app import db
from app.models import Interaction, Post, VisitorSession, utcnow
from app.services.similarity_service import get_related_posts


SESSION_TOKEN_KEY = "reader_session_token"
PAGE_VIEW_TRACKER_KEY = "recent_page_view_timestamps"
DEFAULT_LIMIT = 3
MIN_PERSONALIZED_HISTORY = 2
MAX_DWELL_SECONDS = 1800
PAGE_VIEW_COOLDOWN_SECONDS = 120
EVENT_WEIGHTS = {
    "page_view": 1.0,
    "recommendation_click": 2.0,
    "dwell_time": 1.25,
}


def _content_preview(content, limit=140):
    cleaned = " ".join((content or "").split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def ensure_reader_session():
    session_token = session.get(SESSION_TOKEN_KEY)
    visitor_session = None

    if session_token:
        visitor_session = VisitorSession.query.filter_by(session_token=session_token).first()

    if visitor_session is None:
        session_token = f"reader-{uuid4().hex}"
        visitor_session = VisitorSession(session_token=session_token)
        db.session.add(visitor_session)
        session[SESSION_TOKEN_KEY] = session_token
    else:
        session[SESSION_TOKEN_KEY] = visitor_session.session_token

    visitor_session.last_seen = utcnow()
    db.session.commit()
    return visitor_session


def log_reader_event(post, event_type, *, dwell_time=None):
    visitor_session = ensure_reader_session()
    if event_type == "page_view" and _is_recent_page_view(post.id):
        return None

    interaction = Interaction(
        session_token=visitor_session.session_token,
        post_id=post.id,
        event_type=event_type,
        dwell_time=_normalize_dwell_time(dwell_time),
    )
    db.session.add(interaction)
    visitor_session.last_seen = utcnow()
    db.session.commit()
    if event_type == "page_view":
        _mark_page_view(post.id)
    return interaction


def _normalize_dwell_time(dwell_time):
    if dwell_time is None:
        return None

    try:
        dwell_seconds = int(dwell_time)
    except (TypeError, ValueError):
        return None

    if dwell_seconds < 5:
        return None
    return min(dwell_seconds, MAX_DWELL_SECONDS)


def _recent_page_view_tracker():
    tracker = session.get(PAGE_VIEW_TRACKER_KEY)
    if not isinstance(tracker, dict):
        tracker = {}
    return tracker


def _is_recent_page_view(post_id):
    tracker = _recent_page_view_tracker()
    timestamp = tracker.get(str(post_id))
    if timestamp is None:
        return False

    current_timestamp = int(utcnow().timestamp())
    return current_timestamp - int(timestamp) < PAGE_VIEW_COOLDOWN_SECONDS


def _mark_page_view(post_id):
    tracker = _recent_page_view_tracker()
    tracker[str(post_id)] = int(utcnow().timestamp())
    session[PAGE_VIEW_TRACKER_KEY] = tracker
    session.modified = True


def _session_interactions(session_token):
    return (
        Interaction.query.filter_by(session_token=session_token)
        .order_by(Interaction.timestamp.desc(), Interaction.id.desc())
        .all()
    )


def _recent_unique_posts(interactions, *, limit=3):
    recent_posts = []
    seen_ids = set()
    for interaction in interactions:
        if interaction.post_id in seen_ids or interaction.post is None:
            continue
        recent_posts.append(interaction.post)
        seen_ids.add(interaction.post_id)
        if len(recent_posts) >= limit:
            break
    return recent_posts


def _build_category_preferences(interactions):
    category_scores = defaultdict(float)
    category_dwell = defaultdict(float)

    for interaction in interactions:
        if interaction.post is None or not interaction.post.category:
            continue

        weight = EVENT_WEIGHTS.get(interaction.event_type, 1.0)
        category_scores[interaction.post.category] += weight

        if interaction.dwell_time:
            category_dwell[interaction.post.category] += min(interaction.dwell_time / 120.0, 2.0)

    return category_scores, category_dwell


def _semantic_affinity(candidate_posts, recent_posts):
    affinity = defaultdict(float)
    if not candidate_posts or not recent_posts:
        return affinity

    for recent_post in recent_posts:
        for item in get_related_posts(recent_post, limit=len(candidate_posts), candidate_posts=candidate_posts):
            affinity[item["post_id"]] = max(affinity[item["post_id"]], item["score"])

    return affinity


def _popularity_scores():
    popularity_rows = (
        db.session.query(Interaction.post_id, func.count(Interaction.id))
        .group_by(Interaction.post_id)
        .all()
    )
    if not popularity_rows:
        return {}

    max_count = max(count for _, count in popularity_rows) or 1
    return {post_id: count / max_count for post_id, count in popularity_rows}


def _recency_scores(posts):
    ordered_ids = [
        post.id
        for post in sorted(
            posts,
            key=lambda item: getattr(item, "updated_at", None) or getattr(item, "created_at", None),
            reverse=True,
        )
    ]
    total = len(ordered_ids) or 1
    return {post_id: (total - index) / total for index, post_id in enumerate(ordered_ids)}


def _build_reason(candidate, category_score, semantic_score, popularity_score, is_cold_start):
    if is_cold_start:
        if popularity_score >= 0.6:
            return "Popular with readers across the demo session data."
        return "Fresh content to start shaping this reader profile."

    if category_score >= 0.75:
        return f"Strong match for this reader's {candidate.category} reading pattern."
    if semantic_score >= 0.4:
        return "Closely aligned with topics from recent reading history."
    if popularity_score >= 0.6:
        return "Widely engaged post that fits this session's broader interests."
    return "A balanced next read based on this session's recent behavior."


def _serialize_recommendation(candidate, score, reason, *, previously_viewed=False):
    return {
        "post_id": candidate.id,
        "title": candidate.title,
        "category": candidate.category,
        "meta_description": candidate.meta_description or "",
        "content_preview": _content_preview(candidate.content),
        "score": round(score, 3),
        "reason": reason,
        "previously_viewed": previously_viewed,
    }


def get_personalized_recommendations(current_post, *, limit=DEFAULT_LIMIT):
    visitor_session = ensure_reader_session()
    interactions = _session_interactions(visitor_session.session_token)
    unique_viewed_ids = list(dict.fromkeys(interaction.post_id for interaction in interactions))
    candidate_posts = Post.query.filter(Post.id != current_post.id).order_by(Post.created_at.desc()).all()

    if not candidate_posts:
        return {
            "items": [],
            "is_personalized": False,
            "headline": "Recommended for this reader",
            "description": "Add more posts to unlock personalized recommendations.",
        }

    recommendation_clicks = sum(1 for interaction in interactions if interaction.event_type == "recommendation_click")
    dwell_events = sum(1 for interaction in interactions if interaction.event_type == "dwell_time")
    has_meaningful_history = (
        len(unique_viewed_ids) >= MIN_PERSONALIZED_HISTORY
        or recommendation_clicks > 0
        or dwell_events > 0
    )

    category_scores, category_dwell = _build_category_preferences(interactions)
    popularity_scores = _popularity_scores()
    recency_scores = _recency_scores(candidate_posts)
    recent_posts = _recent_unique_posts(interactions, limit=3) if has_meaningful_history else []
    semantic_scores = _semantic_affinity(candidate_posts, recent_posts)

    max_category_score = max(category_scores.values(), default=0.0) or 1.0
    max_category_dwell = max(category_dwell.values(), default=0.0) or 1.0
    viewed_post_ids = set(unique_viewed_ids)
    ranked = []

    for candidate in candidate_posts:
        category_score = category_scores.get(candidate.category, 0.0) / max_category_score
        semantic_score = semantic_scores.get(candidate.id, 0.0)
        popularity_score = popularity_scores.get(candidate.id, 0.0)
        recency_score = recency_scores.get(candidate.id, 0.0)
        dwell_score = category_dwell.get(candidate.category, 0.0) / max_category_dwell

        if has_meaningful_history:
            score = (
                0.35 * category_score
                + 0.30 * semantic_score
                + 0.20 * popularity_score
                + 0.10 * recency_score
                + 0.05 * dwell_score
            )
        else:
            score = (0.65 * popularity_score) + (0.35 * recency_score)

        previously_viewed = candidate.id in viewed_post_ids
        if previously_viewed:
            score *= 0.35

        ranked.append(
            _serialize_recommendation(
                candidate,
                score,
                _build_reason(
                    candidate,
                    category_score,
                    semantic_score,
                    popularity_score,
                    not has_meaningful_history,
                ),
                previously_viewed=previously_viewed,
            )
        )

    ranked.sort(key=lambda item: (item["score"], not item["previously_viewed"], item["post_id"]), reverse=True)
    items = ranked[: max(int(limit or DEFAULT_LIMIT), 1)]

    if has_meaningful_history:
        description = "Based on the categories, clicks, and reading time captured in this anonymous session."
    else:
        description = "Start exploring posts and this section will adapt after a few reads."

    return {
        "items": items,
        "is_personalized": has_meaningful_history,
        "headline": "Recommended for this reader",
        "description": description,
    }

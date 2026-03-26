from collections import Counter, defaultdict
from datetime import timedelta
from uuid import uuid4

from flask import session

from app import db
from app.models import Interaction, Post, VisitorSession, utcnow
from app.services.similarity_service import get_post_similarity_scores


SESSION_TOKEN_KEY = "reader_session_token"
VIEW_EVENT = "view"
RECOMMENDATION_CLICK_EVENT = "recommendation_click"
RECENT_HISTORY_LIMIT = 5
RECENT_SIMILARITY_LIMIT = 3
DEFAULT_RECOMMENDATION_LIMIT = 4
VIEW_PENALTY = 0.45
RECENT_VIEW_PENALTY = 0.2
DEDUPLICATION_WINDOW = timedelta(minutes=30)

CATEGORY_WEIGHT = 0.35
SEMANTIC_WEIGHT = 0.3
POPULARITY_WEIGHT = 0.2
RECENCY_WEIGHT = 0.1
DWELL_WEIGHT = 0.05

EVENT_SIGNAL_WEIGHTS = {
    VIEW_EVENT: 1.0,
    RECOMMENDATION_CLICK_EVENT: 1.35,
}


def _normalize_scores(score_map):
    if not score_map:
        return {}

    max_score = max(score_map.values())
    if max_score <= 0:
        return {key: 0.0 for key in score_map}
    return {key: value / max_score for key, value in score_map.items()}


def _post_timestamp(post):
    timestamp = post.updated_at or post.created_at or utcnow()
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=utcnow().tzinfo)
    return timestamp


def _normalize_timestamp(timestamp):
    if timestamp is None:
        return utcnow()
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=utcnow().tzinfo)
    return timestamp


class PersonalizationService:
    def get_or_create_session_token(self):
        token = session.get(SESSION_TOKEN_KEY)
        visitor_session = None
        now = utcnow()

        if token:
            visitor_session = VisitorSession.query.filter_by(session_token=token).first()

        if visitor_session is None:
            token = uuid4().hex
            visitor_session = VisitorSession(
                session_token=token,
                first_seen=now,
                last_seen=now,
            )
            db.session.add(visitor_session)
            db.session.commit()
            session[SESSION_TOKEN_KEY] = token
            return token

        visitor_session.last_seen = now
        db.session.commit()
        session[SESSION_TOKEN_KEY] = token
        return token

    def record_interaction(self, session_token, post_id, *, event_type, dwell_time=None):
        now = utcnow()
        recent_match = (
            Interaction.query.filter_by(
                session_token=session_token,
                post_id=post_id,
                event_type=event_type,
            )
            .order_by(Interaction.timestamp.desc())
            .first()
        )
        if recent_match and now - recent_match.timestamp <= DEDUPLICATION_WINDOW:
            if dwell_time is not None and recent_match.dwell_time is None:
                recent_match.dwell_time = dwell_time
                db.session.commit()
            return recent_match

        interaction = Interaction(
            session_token=session_token,
            post_id=post_id,
            event_type=event_type,
            dwell_time=dwell_time,
            timestamp=now,
        )
        db.session.add(interaction)

        visitor_session = VisitorSession.query.filter_by(session_token=session_token).first()
        if visitor_session is not None:
            visitor_session.last_seen = now

        db.session.commit()
        return interaction

    def get_recommendations_for_session(
        self,
        session_token,
        *,
        limit=DEFAULT_RECOMMENDATION_LIMIT,
        exclude_post_id=None,
        candidate_posts=None,
    ):
        normalized_limit = min(max(int(limit or DEFAULT_RECOMMENDATION_LIMIT), 1), 8)
        posts = list(candidate_posts) if candidate_posts is not None else Post.query.order_by(Post.id.asc()).all()
        if exclude_post_id is not None:
            posts = [post for post in posts if post.id != exclude_post_id]
        if not posts:
            return []

        behavior = self._build_behavior_profile(session_token)
        if not behavior["history"]:
            return self._build_cold_start_recommendations(posts, limit=normalized_limit)

        score_context = self._build_score_context(posts, behavior)
        ranked = []
        for post in posts:
            ranked.append(self._score_post(post, behavior, score_context))

        ranked.sort(
            key=lambda item: (
                item["score"],
                item["component_scores"]["semantic_similarity"],
                item["component_scores"]["category_preference"],
                item["component_scores"]["popularity"],
                item["post"].updated_at or item["post"].created_at or utcnow(),
            ),
            reverse=True,
        )
        return [self._serialize_recommendation(item, rank=index + 1) for index, item in enumerate(ranked[:normalized_limit])]

    def _build_behavior_profile(self, session_token):
        interactions = (
            Interaction.query.filter_by(session_token=session_token)
            .order_by(Interaction.timestamp.desc())
            .all()
        )
        history = []
        category_scores = Counter()
        viewed_post_ids = set()
        recent_viewed_post_ids = []
        category_dwell = defaultdict(list)

        for interaction in interactions:
            post = interaction.post
            if post is None:
                continue

            signal_weight = EVENT_SIGNAL_WEIGHTS.get(interaction.event_type, 0.8)
            dwell_minutes = min((interaction.dwell_time or 0) / 240.0, 1.0)
            behavior_weight = signal_weight + dwell_minutes * 0.35

            history.append(
                {
                    "post": post,
                    "post_id": post.id,
                    "category": post.category,
                    "event_type": interaction.event_type,
                    "dwell_time": interaction.dwell_time or 0,
                    "timestamp": _normalize_timestamp(interaction.timestamp),
                    "weight": behavior_weight,
                }
            )

            category_scores[post.category] += behavior_weight
            viewed_post_ids.add(post.id)

            if post.category and interaction.dwell_time:
                category_dwell[post.category].append(interaction.dwell_time)

            if interaction.event_type == VIEW_EVENT and post.id not in recent_viewed_post_ids:
                recent_viewed_post_ids.append(post.id)

        return {
            "history": history,
            "category_scores": _normalize_scores(category_scores),
            "viewed_post_ids": viewed_post_ids,
            "recent_viewed_post_ids": recent_viewed_post_ids[:RECENT_HISTORY_LIMIT],
            "recent_seed_posts": [entry["post"] for entry in history if entry["event_type"] == VIEW_EVENT][:RECENT_SIMILARITY_LIMIT],
            "category_dwell": {
                category: min(sum(dwell_times) / len(dwell_times) / 360.0, 1.0)
                for category, dwell_times in category_dwell.items()
            },
        }

    def _build_score_context(self, posts, behavior):
        popularity_scores = self._build_popularity_scores(posts)
        recency_scores = self._build_recency_scores(posts)
        semantic_scores = self._build_semantic_scores(posts, behavior["recent_seed_posts"])

        return {
            "popularity": popularity_scores,
            "recency": recency_scores,
            "semantic": semantic_scores,
        }

    def _build_popularity_scores(self, posts):
        post_ids = [post.id for post in posts]
        if not post_ids:
            return {}

        popularity = Counter()
        interactions = Interaction.query.filter(Interaction.post_id.in_(post_ids)).all()
        for interaction in interactions:
            base = 1.0 if interaction.event_type == VIEW_EVENT else 1.4
            dwell_boost = min((interaction.dwell_time or 0) / 300.0, 0.4)
            popularity[interaction.post_id] += base + dwell_boost
        return _normalize_scores(popularity)

    def _build_recency_scores(self, posts):
        if not posts:
            return {}

        now = utcnow()
        recency_scores = {}
        for post in posts:
            age_days = max((now - _post_timestamp(post)).days, 0)
            recency_scores[post.id] = 1.0 / (1.0 + age_days / 14.0)
        return _normalize_scores(recency_scores)

    def _build_semantic_scores(self, posts, recent_posts):
        if not posts or not recent_posts:
            return {}

        candidate_posts = list(posts)
        aggregated = Counter()
        weights = []
        for index, recent_post in enumerate(recent_posts[:RECENT_SIMILARITY_LIMIT]):
            similarity_map = get_post_similarity_scores(recent_post, candidate_posts=candidate_posts)
            decay = max(0.45, 1.0 - index * 0.2)
            weights.append(decay)
            for post_id, similarity_score in similarity_map.items():
                aggregated[post_id] += similarity_score * decay

        total_weight = sum(weights) or 1.0
        normalized = {post_id: score / total_weight for post_id, score in aggregated.items()}
        return _normalize_scores(normalized)

    def _score_post(self, post, behavior, score_context):
        category_preference = behavior["category_scores"].get(post.category, 0.0)
        semantic_similarity = score_context["semantic"].get(post.id, 0.0)
        popularity = score_context["popularity"].get(post.id, 0.0)
        recency = score_context["recency"].get(post.id, 0.0)
        dwell_affinity = behavior["category_dwell"].get(post.category, 0.0)

        score = (
            CATEGORY_WEIGHT * category_preference
            + SEMANTIC_WEIGHT * semantic_similarity
            + POPULARITY_WEIGHT * popularity
            + RECENCY_WEIGHT * recency
            + DWELL_WEIGHT * dwell_affinity
        )

        viewed_penalty = 0.0
        if post.id in behavior["viewed_post_ids"]:
            viewed_penalty += VIEW_PENALTY
        if post.id in behavior["recent_viewed_post_ids"]:
            viewed_penalty += RECENT_VIEW_PENALTY

        score = max(score - viewed_penalty, 0.0)
        explanation = self._build_explanation(
            post,
            category_preference=category_preference,
            semantic_similarity=semantic_similarity,
            popularity=popularity,
            recency=recency,
            dwell_affinity=dwell_affinity,
            viewed_penalty=viewed_penalty,
        )

        return {
            "post": post,
            "score": round(score, 4),
            "component_scores": {
                "category_preference": round(category_preference, 4),
                "semantic_similarity": round(semantic_similarity, 4),
                "popularity": round(popularity, 4),
                "recency": round(recency, 4),
                "dwell_time_affinity": round(dwell_affinity, 4),
                "viewed_penalty": round(viewed_penalty, 4),
            },
            "already_viewed": post.id in behavior["viewed_post_ids"],
            "reasons": explanation,
        }

    def _build_cold_start_recommendations(self, posts, *, limit):
        score_context = {
            "popularity": self._build_popularity_scores(posts),
            "recency": self._build_recency_scores(posts),
        }

        ranked = []
        for post in posts:
            popularity = score_context["popularity"].get(post.id, 0.0)
            recency = score_context["recency"].get(post.id, 0.0)
            score = round(popularity * 0.65 + recency * 0.35, 4)
            ranked.append(
                {
                    "post": post,
                    "score": score,
                    "component_scores": {
                        "category_preference": 0.0,
                        "semantic_similarity": 0.0,
                        "popularity": round(popularity, 4),
                        "recency": round(recency, 4),
                        "dwell_time_affinity": 0.0,
                        "viewed_penalty": 0.0,
                    },
                    "already_viewed": False,
                    "reasons": ["popular with readers", "recently updated"],
                    "cold_start": True,
                }
            )

        ranked.sort(
            key=lambda item: (
                item["score"],
                item["component_scores"]["popularity"],
                item["component_scores"]["recency"],
            ),
            reverse=True,
        )
        return [self._serialize_recommendation(item, rank=index + 1) for index, item in enumerate(ranked[:limit])]

    def _build_explanation(
        self,
        post,
        *,
        category_preference,
        semantic_similarity,
        popularity,
        recency,
        dwell_affinity,
        viewed_penalty,
    ):
        reasons = []
        if category_preference >= 0.45:
            reasons.append(f"matches your interest in {post.category}")
        if semantic_similarity >= 0.35:
            reasons.append("similar to posts you read recently")
        if popularity >= 0.45:
            reasons.append("performing well with readers")
        if recency >= 0.55:
            reasons.append("fresh content")
        if dwell_affinity >= 0.35:
            reasons.append("fits topics you spend more time reading")
        if viewed_penalty > 0:
            reasons.append("already viewed, so ranked lower")
        return reasons or ["general relevance from recent activity"]

    def _serialize_recommendation(self, scored_item, *, rank):
        post = scored_item["post"]
        return {
            "rank": rank,
            "post": post,
            "post_id": post.id,
            "title": post.title,
            "category": post.category,
            "meta_description": post.meta_description or "",
            "tags": [tag.strip() for tag in (post.tags or "").split(",") if tag.strip()],
            "score": round(scored_item["score"], 3),
            "already_viewed": scored_item["already_viewed"],
            "reasons": scored_item["reasons"],
            "component_scores": scored_item["component_scores"],
            "is_cold_start": scored_item.get("cold_start", False),
            "updated_at": _post_timestamp(post).isoformat(),
        }


personalization_service = PersonalizationService()


def ensure_reader_session():
    return personalization_service.get_or_create_session_token()


def record_post_view(session_token, post_id, *, dwell_time=None):
    return personalization_service.record_interaction(
        session_token,
        post_id,
        event_type=VIEW_EVENT,
        dwell_time=dwell_time,
    )


def record_recommendation_click(session_token, post_id, *, dwell_time=None):
    return personalization_service.record_interaction(
        session_token,
        post_id,
        event_type=RECOMMENDATION_CLICK_EVENT,
        dwell_time=dwell_time,
    )


def get_personalized_recommendations(session_token, *, limit=DEFAULT_RECOMMENDATION_LIMIT, exclude_post_id=None):
    return personalization_service.get_recommendations_for_session(
        session_token,
        limit=limit,
        exclude_post_id=exclude_post_id,
    )

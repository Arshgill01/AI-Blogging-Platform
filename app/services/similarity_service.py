import math
import re
from collections import Counter
from datetime import timezone

from app.models import Post, utcnow


TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]+")


def _tokenize(text):
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text or "")]


def _split_tags(tags):
    return [tag.strip() for tag in (tags or "").split(",") if tag.strip()]


def build_post_document(*, title="", content="", category="", tags=""):
    title = (title or "").strip()
    content = (content or "").strip()
    category = (category or "").strip()
    tag_list = _split_tags(tags)

    parts = []
    if title:
        parts.extend([title] * 3)
    if category:
        parts.extend([category] * 2)
    if tag_list:
        tag_text = " ".join(tag_list)
        parts.extend([tag_text] * 2)
    if content:
        parts.append(content)
    return "\n".join(parts)


def _tfidf_vector(documents):
    tokenized_documents = [_tokenize(document) for document in documents]
    if not any(tokenized_documents):
        return tokenized_documents, []

    document_frequency = Counter()
    for tokens in tokenized_documents:
        document_frequency.update(set(tokens))

    doc_count = len(tokenized_documents)
    vectors = []
    for tokens in tokenized_documents:
        term_counts = Counter(tokens)
        token_total = sum(term_counts.values())
        if not token_total:
            vectors.append({})
            continue

        vector = {}
        for term, count in term_counts.items():
            tf = count / token_total
            idf = math.log((1 + doc_count) / (1 + document_frequency[term])) + 1.0
            vector[term] = tf * idf
        vectors.append(vector)

    return tokenized_documents, vectors


def _cosine_similarity(left, right):
    if not left or not right:
        return 0.0

    shared_terms = set(left).intersection(right)
    numerator = sum(left[term] * right[term] for term in shared_terms)
    if numerator <= 0:
        return 0.0

    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if not left_norm or not right_norm:
        return 0.0

    return numerator / (left_norm * right_norm)


def _recency_boost(post):
    timestamp = getattr(post, "updated_at", None) or getattr(post, "created_at", None)
    if timestamp is None:
        return 0.0
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    age_days = max((utcnow() - timestamp).days, 0)
    freshness = max(0.0, 1.0 - min(age_days, 365) / 365)
    return freshness * 0.03


def _serialize_related_post(post, *, cosine_score, score, shared_tags, category_match):
    reasons = []
    if category_match:
        reasons.append("same-category")
    if shared_tags:
        reasons.append("shared-tags")
    if cosine_score > 0:
        reasons.append("content-overlap")

    return {
        "post_id": post.id,
        "title": post.title,
        "category": post.category,
        "tags": _split_tags(post.tags),
        "similarity_score": round(cosine_score, 4),
        "score": round(score, 4),
        "shared_tags": shared_tags,
        "reason_codes": reasons,
    }


def _is_strong_match(*, cosine_score, category_match, shared_tags):
    if cosine_score >= 0.2:
        return True
    if category_match and cosine_score >= 0.12:
        return True
    if shared_tags and cosine_score >= 0.1:
        return True
    return False


class SimilarityService:
    def build_document(self, *, title="", content="", category="", tags=""):
        return build_post_document(
            title=title,
            content=content,
            category=category,
            tags=tags,
        )

    def get_related_posts(self, post, *, limit=3, candidate_posts=None):
        return self.get_related_posts_for_fields(
            title=post.title,
            content=post.content,
            category=post.category,
            tags=post.tags,
            limit=limit,
            exclude_post_id=post.id,
            candidate_posts=candidate_posts,
        )

    def get_related_posts_for_fields(
        self,
        *,
        title,
        content,
        category="",
        tags="",
        limit=3,
        exclude_post_id=None,
        candidate_posts=None,
    ):
        normalized_limit = min(max(int(limit or 3), 1), 5)
        candidates = list(candidate_posts) if candidate_posts is not None else Post.query.order_by(Post.id.asc()).all()
        candidates = [post for post in candidates if exclude_post_id is None or post.id != exclude_post_id]
        if not candidates:
            return []

        target_document = self.build_document(
            title=title,
            content=content,
            category=category,
            tags=tags,
        )
        documents = [target_document]
        documents.extend(
            self.build_document(
                title=post.title,
                content=post.content,
                category=post.category,
                tags=post.tags,
            )
            for post in candidates
        )

        _, vectors = _tfidf_vector(documents)
        if not vectors:
            return []

        target_vector = vectors[0]
        if not target_vector:
            return []

        target_category = (category or "").strip().lower()
        target_tags = {tag.lower() for tag in _split_tags(tags)}

        primary_results = []
        fallback_results = []
        for post, candidate_vector in zip(candidates, vectors[1:]):
            cosine_score = _cosine_similarity(target_vector, candidate_vector)
            candidate_category = (post.category or "").strip().lower()
            candidate_tags = {tag.lower() for tag in _split_tags(post.tags)}
            shared_tags = sorted(target_tags.intersection(candidate_tags))
            category_match = bool(target_category and candidate_category and target_category == candidate_category)

            score = cosine_score
            if category_match:
                score += 0.08
            if shared_tags:
                score += min(0.02 * len(shared_tags), 0.08)
            score += _recency_boost(post)

            if cosine_score <= 0 and not category_match and not shared_tags:
                continue

            serialized = _serialize_related_post(
                post,
                cosine_score=cosine_score,
                score=score,
                shared_tags=shared_tags,
                category_match=category_match,
            )
            if _is_strong_match(
                cosine_score=cosine_score,
                category_match=category_match,
                shared_tags=shared_tags,
            ):
                primary_results.append(serialized)
            else:
                fallback_results.append(serialized)

        primary_results.sort(
            key=lambda item: (item["score"], item["similarity_score"], item["post_id"]),
            reverse=True,
        )
        fallback_results.sort(
            key=lambda item: (item["score"], item["similarity_score"], item["post_id"]),
            reverse=True,
        )
        return (primary_results + fallback_results)[:normalized_limit]


similarity_service = SimilarityService()


def get_related_posts(post, *, limit=3, candidate_posts=None):
    return similarity_service.get_related_posts(
        post,
        limit=limit,
        candidate_posts=candidate_posts,
    )


def get_related_posts_for_fields(
    *,
    title,
    content,
    category="",
    tags="",
    limit=3,
    exclude_post_id=None,
    candidate_posts=None,
):
    return similarity_service.get_related_posts_for_fields(
        title=title,
        content=content,
        category=category,
        tags=tags,
        limit=limit,
        exclude_post_id=exclude_post_id,
        candidate_posts=candidate_posts,
    )


def suggest_internal_links(post, *, limit=5, candidate_posts=None):
    return get_related_posts(
        post,
        limit=limit,
        candidate_posts=candidate_posts,
    )

import math
import re
from collections import Counter
from types import SimpleNamespace

from app.models import Post


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "before",
    "being",
    "between",
    "both",
    "could",
    "does",
    "each",
    "every",
    "from",
    "have",
    "into",
    "just",
    "like",
    "more",
    "most",
    "much",
    "only",
    "other",
    "over",
    "same",
    "should",
    "some",
    "such",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")
MINIMUM_SCORE = 0.18
MINIMUM_RAW_SIMILARITY = 0.03
MAX_RESULTS = 3


def _tokenize(text):
    return [match.group(0).lower() for match in WORD_RE.finditer(text or "")]


def _normalize_token(token):
    token = token.lower().strip("-'")
    if len(token) > 4:
        for suffix in ("ingly", "edly", "ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                token = token[: -len(suffix)]
                break
    return token


def _normalized_terms(text):
    terms = []
    for token in _tokenize(text):
        normalized = _normalize_token(token)
        if len(normalized) >= 3 and normalized not in STOPWORDS:
            terms.append(normalized)
    return terms


def _normalized_bigrams(text):
    terms = _normalized_terms(text)
    return [f"{left}_{right}" for left, right in zip(terms, terms[1:])]


def _parse_tags(tags):
    return [tag.strip() for tag in (tags or "").split(",") if tag.strip()]


def _normalized_tags(tags):
    return [tag.lower() for tag in _parse_tags(tags)]


def _content_preview(content, limit=160):
    cleaned = " ".join((content or "").split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def build_post_document(*, title="", content="", category="", tags="", meta_description=""):
    title = (title or "").strip()
    content = (content or "").strip()
    category = (category or "").strip()
    meta_description = (meta_description or "").strip()
    tag_list = _parse_tags(tags)

    parts = []
    if title:
        parts.extend([title] * 3)
    if category:
        parts.extend([category] * 2)
    if tag_list:
        tag_text = " ".join(tag_list)
        parts.extend([tag_text] * 2)
    if meta_description:
        parts.append(meta_description)
    if content:
        parts.append(content)
    return "\n".join(parts)


def _build_document_terms(post):
    counts = Counter()

    def add_terms(text, weight, *, include_bigrams=False, bigram_weight=None):
        for term in _normalized_terms(text):
            counts[term] += weight
        if include_bigrams:
            for term in _normalized_bigrams(text):
                counts[term] += bigram_weight if bigram_weight is not None else weight

    add_terms(post.title, 4, include_bigrams=True, bigram_weight=3)
    add_terms(post.category, 2, include_bigrams=True, bigram_weight=2)
    add_terms(post.tags or "", 3, include_bigrams=True, bigram_weight=2.5)
    add_terms(getattr(post, "meta_description", "") or "", 2, include_bigrams=True, bigram_weight=1.5)
    add_terms(post.content, 1, include_bigrams=True, bigram_weight=0.35)
    return counts


def _build_tfidf_vectors(posts):
    documents = {}
    document_frequency = Counter()

    for post in posts:
        terms = _build_document_terms(post)
        documents[post.id] = terms
        for term in terms:
            document_frequency[term] += 1

    total_documents = len(posts)
    vectors = {}
    norms = {}

    for post_id, terms in documents.items():
        vector = {}
        norm = 0.0
        for term, count in terms.items():
            idf = math.log((1 + total_documents) / (1 + document_frequency[term])) + 1.0
            weight = (1.0 + math.log(count)) * idf
            vector[term] = weight
            norm += weight * weight
        vectors[post_id] = vector
        norms[post_id] = math.sqrt(norm) if norm > 0 else 0.0

    return vectors, norms


def _cosine_similarity(left_vector, left_norm, right_vector, right_norm):
    if not left_norm or not right_norm:
        return 0.0

    if len(left_vector) > len(right_vector):
        left_vector, right_vector = right_vector, left_vector

    dot_product = sum(weight * right_vector.get(term, 0.0) for term, weight in left_vector.items())
    if not dot_product:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _shared_terms(left_vector, right_vector, limit=3):
    shared = []
    for term in set(left_vector) & set(right_vector):
        shared.append((term, left_vector[term] + right_vector[term]))
    shared.sort(key=lambda item: item[1], reverse=True)
    return [term.replace("_", " ") for term, _ in shared[:limit]]


def _tag_overlap(source_tags, candidate_tags):
    source_set = set(source_tags)
    candidate_set = set(candidate_tags)
    if not source_set or not candidate_set:
        return []
    return sorted(source_set & candidate_set)


def _category_boost(source_post, candidate_post):
    return 0.06 if source_post.category and source_post.category == candidate_post.category else 0.0


def _tag_boost(shared_tags, source_tags, candidate_tags):
    if not shared_tags:
        return 0.0

    denominator = max(len(set(source_tags) | set(candidate_tags)), 1)
    overlap_ratio = len(shared_tags) / denominator
    return min(0.08, 0.08 * overlap_ratio + 0.02)


def _recency_key(post):
    timestamp = getattr(post, "updated_at", None) or getattr(post, "created_at", None)
    return timestamp.isoformat() if timestamp else ""


def _serialize_result(candidate, raw_similarity, score, shared_tags, strength, same_category, shared_terms):
    display_tags = _parse_tags(candidate.tags)
    anchor_hint = ", ".join(shared_tags[:2] or shared_terms[:2]) or candidate.title
    reasons = []
    if same_category:
        reasons.append("same-category")
    if shared_tags:
        reasons.append("shared-tags")
    if raw_similarity > 0:
        reasons.append("content-overlap")

    return {
        "post": candidate,
        "post_id": candidate.id,
        "title": candidate.title,
        "category": candidate.category,
        "tags": display_tags,
        "score": round(score, 3),
        "raw_similarity": round(raw_similarity, 3),
        "similarity_score": round(raw_similarity, 4),
        "similarity_percent": max(1, min(100, round(raw_similarity * 100))) if raw_similarity > 0 else 1,
        "same_category": same_category,
        "category_match": same_category,
        "shared_tags": shared_tags,
        "shared_terms": shared_terms,
        "match_strength": strength,
        "reason_codes": reasons,
        "anchor_hint": anchor_hint,
        "meta_description": getattr(candidate, "meta_description", "") or "",
        "content_preview": _content_preview(candidate.content),
        "updated_at": _recency_key(candidate) or None,
    }


def related_post_payload(results):
    payload = []
    for result in results:
        payload.append(
            {
                "post_id": result["post_id"],
                "title": result["title"],
                "category": result["category"],
                "score": result["score"],
                "raw_similarity": result["raw_similarity"],
                "similarity_score": result["similarity_score"],
                "similarity_percent": result["similarity_percent"],
                "same_category": result["same_category"],
                "category_match": result["category_match"],
                "shared_tags": result["shared_tags"],
                "shared_terms": result["shared_terms"],
                "match_strength": result["match_strength"],
                "reason_codes": result["reason_codes"],
                "anchor_hint": result["anchor_hint"],
                "meta_description": result["meta_description"],
                "content_preview": result["content_preview"],
                "updated_at": result["updated_at"],
            }
        )
    return payload


def _public_results(results):
    sanitized = []
    for result in results:
        public_result = dict(result)
        public_result.pop("post", None)
        sanitized.append(public_result)
    return sanitized


class SimilarityService:
    def build_document(self, *, title="", content="", category="", tags="", meta_description=""):
        return build_post_document(
            title=title,
            content=content,
            category=category,
            tags=tags,
            meta_description=meta_description,
        )

    def get_related_posts(self, post, *, limit=3, candidate_posts=None):
        return self.get_related_posts_for_fields(
            title=post.title,
            content=post.content,
            category=post.category,
            tags=post.tags,
            meta_description=getattr(post, "meta_description", ""),
            limit=limit,
            exclude_post_id=post.id,
            candidate_posts=candidate_posts,
        )

    def get_similarity_scores(self, post, *, candidate_posts=None):
        candidates = list(candidate_posts) if candidate_posts is not None else Post.query.order_by(Post.id.asc()).all()
        candidates = [candidate for candidate in candidates if candidate.id != post.id]
        if not candidates:
            return {}

        corpus = [post, *candidates]
        vectors, norms = _build_tfidf_vectors(corpus)
        source_vector = vectors.get(post.id, {})
        source_norm = norms.get(post.id, 0.0)
        if not source_vector or not source_norm:
            return {}

        similarity_scores = {}
        for candidate in candidates:
            similarity_scores[candidate.id] = _cosine_similarity(
                source_vector,
                source_norm,
                vectors.get(candidate.id, {}),
                norms.get(candidate.id, 0.0),
            )
        return similarity_scores

    def get_related_posts_for_fields(
        self,
        *,
        title,
        content,
        category="",
        tags="",
        meta_description="",
        limit=3,
        exclude_post_id=None,
        candidate_posts=None,
    ):
        normalized_limit = min(max(int(limit or 3), 1), 5)
        candidates = list(candidate_posts) if candidate_posts is not None else Post.query.order_by(Post.id.asc()).all()
        candidates = [post for post in candidates if exclude_post_id is None or post.id != exclude_post_id]
        if not candidates:
            return []

        target_post = SimpleNamespace(
            id=exclude_post_id if exclude_post_id is not None else 0,
            title=title,
            content=content,
            category=category,
            tags=tags,
            meta_description=meta_description,
            created_at=None,
            updated_at=None,
        )
        corpus = [target_post, *candidates]
        vectors, norms = _build_tfidf_vectors(corpus)
        source_vector = vectors.get(target_post.id, {})
        source_norm = norms.get(target_post.id, 0.0)
        if not source_vector or not source_norm:
            return []

        source_tags = _normalized_tags(tags)
        ranked = []
        fallback = []

        for candidate in candidates:
            candidate_tags = _normalized_tags(candidate.tags)
            shared_tags = _tag_overlap(source_tags, candidate_tags)
            same_category = bool(category and candidate.category and category == candidate.category)
            candidate_vector = vectors.get(candidate.id, {})
            raw_similarity = _cosine_similarity(
                source_vector,
                source_norm,
                candidate_vector,
                norms.get(candidate.id, 0.0),
            )
            score = raw_similarity + _category_boost(target_post, candidate) + _tag_boost(
                shared_tags, source_tags, candidate_tags
            )

            shared_terms = _shared_terms(source_vector, candidate_vector)
            strong_result = _serialize_result(
                candidate,
                raw_similarity,
                score,
                shared_tags,
                "strong",
                same_category,
                shared_terms,
            )
            fallback_result = _serialize_result(
                candidate,
                raw_similarity,
                score,
                shared_tags,
                "fallback",
                same_category,
                shared_terms,
            )
            ranked.append(strong_result)
            fallback.append(fallback_result)

        strong_results = [
            result
            for result in ranked
            if result["score"] >= MINIMUM_SCORE
            and (
                result["raw_similarity"] >= MINIMUM_RAW_SIMILARITY
                or result["same_category"]
                or result["shared_tags"]
            )
        ]
        strong_results.sort(
            key=lambda result: (
                result["score"],
                result["raw_similarity"],
                result["same_category"],
                len(result["shared_tags"]),
                _recency_key(result["post"]),
            ),
            reverse=True,
        )

        fallback.sort(
            key=lambda result: (
                result["same_category"],
                len(result["shared_tags"]),
                result["raw_similarity"],
                _recency_key(result["post"]),
            ),
            reverse=True,
        )

        if not strong_results:
            return _public_results(fallback[:normalized_limit])

        selected_results = strong_results[:normalized_limit]
        if len(selected_results) >= normalized_limit:
            return _public_results(selected_results)

        selected_ids = {result["post_id"] for result in selected_results}
        for result in fallback:
            if result["post_id"] in selected_ids:
                continue
            selected_results.append(result)
            selected_ids.add(result["post_id"])
            if len(selected_results) >= normalized_limit:
                break

        return _public_results(selected_results)


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
    meta_description="",
    limit=3,
    exclude_post_id=None,
    candidate_posts=None,
):
    return similarity_service.get_related_posts_for_fields(
        title=title,
        content=content,
        category=category,
        tags=tags,
        meta_description=meta_description,
        limit=limit,
        exclude_post_id=exclude_post_id,
        candidate_posts=candidate_posts,
    )


def get_post_similarity_scores(post, *, candidate_posts=None):
    return similarity_service.get_similarity_scores(post, candidate_posts=candidate_posts)


def suggest_internal_links(post, *, limit=5, candidate_posts=None):
    return get_related_posts(
        post,
        limit=limit,
        candidate_posts=candidate_posts,
    )


def get_internal_link_suggestions(post, limit=4):
    return suggest_internal_links(post, limit=limit)

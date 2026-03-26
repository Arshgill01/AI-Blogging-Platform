import math
import re
from collections import Counter

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
    return [tag.strip().lower() for tag in (tags or "").split(",") if tag.strip()]


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
    add_terms(post.meta_description or "", 2, include_bigrams=True, bigram_weight=1.5)
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
    created_at = getattr(post, "created_at", None)
    return created_at.isoformat() if created_at else ""


def _serialize_result(candidate, raw_similarity, score, shared_tags, strength):
    return {
        "post": candidate,
        "post_id": candidate.id,
        "title": candidate.title,
        "category": candidate.category,
        "tags": _parse_tags(candidate.tags),
        "score": round(score, 3),
        "raw_similarity": round(raw_similarity, 3),
        "same_category": False,
        "shared_tags": shared_tags,
        "match_strength": strength,
    }


def _to_public_result(candidate, raw_similarity, score, shared_tags, strength, same_category):
    result = _serialize_result(candidate, raw_similarity, score, shared_tags, strength)
    result["same_category"] = same_category
    return result


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
                "same_category": result["same_category"],
                "shared_tags": result["shared_tags"],
                "match_strength": result["match_strength"],
            }
        )
    return payload


def get_related_posts(post, *, posts=None, limit=MAX_RESULTS):
    if post is None or getattr(post, "id", None) is None:
        return []

    if posts is None:
        posts = Post.query.order_by(Post.created_at.desc(), Post.id.desc()).all()

    candidates = [candidate for candidate in posts if candidate.id != post.id]
    if not candidates:
        return []

    corpus = [post, *candidates]
    vectors, norms = _build_tfidf_vectors(corpus)
    source_vector = vectors.get(post.id, {})
    source_norm = norms.get(post.id, 0.0)
    source_tags = _parse_tags(post.tags)

    ranked = []
    fallback = []

    for candidate in candidates:
        candidate_tags = _parse_tags(candidate.tags)
        shared_tags = _tag_overlap(source_tags, candidate_tags)
        same_category = bool(post.category and post.category == candidate.category)
        raw_similarity = _cosine_similarity(
            source_vector,
            source_norm,
            vectors.get(candidate.id, {}),
            norms.get(candidate.id, 0.0),
        )
        score = raw_similarity + _category_boost(post, candidate) + _tag_boost(
            shared_tags, source_tags, candidate_tags
        )

        public_result = _to_public_result(
            candidate,
            raw_similarity=raw_similarity,
            score=score,
            shared_tags=shared_tags,
            strength="strong",
            same_category=same_category,
        )
        ranked.append(public_result)

        fallback_result = _to_public_result(
            candidate,
            raw_similarity=raw_similarity,
            score=score,
            shared_tags=shared_tags,
            strength="fallback",
            same_category=same_category,
        )
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
        return fallback[:limit]

    selected_results = strong_results[:limit]
    if len(selected_results) >= limit:
        return selected_results

    selected_ids = {result["post_id"] for result in selected_results}

    for result in fallback:
        if result["post_id"] in selected_ids:
            continue
        selected_results.append(result)
        selected_ids.add(result["post_id"])
        if len(selected_results) >= limit:
            break

    return selected_results

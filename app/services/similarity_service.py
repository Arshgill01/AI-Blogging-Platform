import math
import re
from collections import Counter

from app.models import Post


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")
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


def _tokenize(text):
    return [
        match.group(0).lower()
        for match in TOKEN_RE.finditer(text or "")
        if len(match.group(0)) >= 3 and match.group(0).lower() not in STOPWORDS
    ]


def _normalize_tags(tags):
    return [tag.strip().lower() for tag in (tags or "").split(",") if tag.strip()]


def _content_preview(content, limit=160):
    cleaned = " ".join((content or "").split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def _build_document(post):
    title = (post.title or "").strip()
    category = (post.category or "").strip()
    tags = " ".join(_normalize_tags(post.tags))
    content = (post.content or "").strip()

    weighted_text = "\n".join(
        part for part in (title, title, category, tags, content) if part
    )
    return Counter(_tokenize(weighted_text))


def _build_tfidf_vectors(posts):
    documents = [(post, _build_document(post)) for post in posts]
    non_empty_documents = [(post, counter) for post, counter in documents if counter]
    if len(non_empty_documents) < 2:
        return {}

    document_frequency = Counter()
    for _, counter in non_empty_documents:
        document_frequency.update(counter.keys())

    total_documents = len(non_empty_documents)
    vectors = {}
    for post, counter in non_empty_documents:
        max_count = max(counter.values())
        vector = {}
        for term, count in counter.items():
            tf = count / max_count
            idf = math.log((1 + total_documents) / (1 + document_frequency[term])) + 1
            vector[term] = tf * idf
        vectors[post.id] = vector

    return vectors


def _cosine_similarity(left, right):
    if not left or not right:
        return 0.0

    shared_terms = set(left) & set(right)
    numerator = sum(left[term] * right[term] for term in shared_terms)
    left_magnitude = math.sqrt(sum(value * value for value in left.values()))
    right_magnitude = math.sqrt(sum(value * value for value in right.values()))
    if not left_magnitude or not right_magnitude:
        return 0.0

    return numerator / (left_magnitude * right_magnitude)


def _shared_terms(source_vector, candidate_vector, limit=3):
    shared = []
    for term in set(source_vector) & set(candidate_vector):
        shared.append((term, source_vector[term] + candidate_vector[term]))
    shared.sort(key=lambda item: item[1], reverse=True)
    return [term for term, _ in shared[:limit]]


def _format_related_post(source_post, candidate_post, source_vector, candidate_vector, score):
    tag_overlap = sorted(
        set(_normalize_tags(source_post.tags)) & set(_normalize_tags(candidate_post.tags))
    )
    shared_terms = _shared_terms(source_vector, candidate_vector)
    anchor_hint = ", ".join(tag_overlap[:2] or shared_terms[:2]) or candidate_post.title

    return {
        "post_id": candidate_post.id,
        "title": candidate_post.title,
        "category": candidate_post.category,
        "meta_description": candidate_post.meta_description or "",
        "content_preview": _content_preview(candidate_post.content),
        "updated_at": candidate_post.updated_at.isoformat()
        if candidate_post.updated_at
        else (candidate_post.created_at.isoformat() if candidate_post.created_at else None),
        "score": round(score, 3),
        "similarity_percent": max(1, round(score * 100)),
        "shared_terms": shared_terms,
        "tag_overlap": tag_overlap,
        "category_match": source_post.category == candidate_post.category,
        "anchor_hint": anchor_hint,
    }


def get_related_posts(post, limit=3):
    if post is None or getattr(post, "id", None) is None:
        return []

    posts = Post.query.order_by(Post.created_at.desc()).all()
    if len(posts) < 2:
        return []

    vectors = _build_tfidf_vectors(posts)
    source_vector = vectors.get(post.id)
    if not source_vector:
        return []

    results = []
    for candidate in posts:
        if candidate.id == post.id:
            continue
        candidate_vector = vectors.get(candidate.id)
        if not candidate_vector:
            continue

        score = _cosine_similarity(source_vector, candidate_vector)
        if score <= 0:
            continue

        results.append(
            _format_related_post(post, candidate, source_vector, candidate_vector, score)
        )

    results.sort(
        key=lambda item: (
            item["score"],
            item["category_match"],
            item["updated_at"] or "",
        ),
        reverse=True,
    )
    return results[:limit]


def get_internal_link_suggestions(post, limit=4):
    return get_related_posts(post, limit=limit)

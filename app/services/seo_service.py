import json
import math
import re
from collections import Counter

from app import db
from app.models import SEOReport

try:
    import textstat
except ImportError:  # pragma: no cover - optional dependency
    textstat = None


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
HTML_HEADING_RE = re.compile(r"<h[1-6][^>]*>.*?</h[1-6]>", re.IGNORECASE | re.DOTALL)


def _tokenize(text):
    return [match.group(0).lower() for match in WORD_RE.finditer(text or "")]


def _count_sentences(text):
    sentences = re.findall(r"[.!?]+(?:\s|$)", text or "")
    return max(len(sentences), 1)


def _normalize_keyword(token):
    token = token.lower().strip("-'")
    if len(token) > 4:
        for suffix in ("ingly", "edly", "ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                token = token[: -len(suffix)]
                break
    return token


def _heading_lines(text):
    lines = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if re.match(r"^\s{0,3}#{1,6}\s+\S+", raw_line):
            lines.append(line.lstrip("# ").strip())
            continue

        if re.match(r"^(?:[A-Z][A-Za-z0-9/&(),:' -]{2,80})$", line) and len(line.split()) <= 10:
            if not line.endswith((".", "!", "?")):
                lines.append(line)
                continue

        if line.endswith(":") and 1 <= len(line.split()) <= 8:
            lines.append(line.rstrip(":"))

    for html_heading in HTML_HEADING_RE.findall(text or ""):
        cleaned = re.sub(r"<[^>]+>", "", html_heading).strip()
        if cleaned:
            lines.append(cleaned)

    return lines


def _count_syllables(word):
    cleaned = re.sub(r"[^a-z]", "", word.lower())
    if not cleaned:
        return 1

    groups = re.findall(r"[aeiouy]+", cleaned)
    syllables = len(groups)

    if cleaned.endswith("e") and syllables > 1:
        syllables -= 1
    if cleaned.endswith("le") and len(cleaned) > 2 and cleaned[-3] not in "aeiouy":
        syllables += 1

    return max(syllables, 1)


def _readability_score(text, words, sentence_count):
    if not words:
        return 0.0
    if textstat is not None:
        try:
            return round(max(min(float(textstat.flesch_reading_ease(text)), 100.0), 0.0), 1)
        except Exception:  # pragma: no cover - defensive fallback
            pass

    syllable_count = sum(_count_syllables(word) for word in words)
    score = 206.835 - 1.015 * (len(words) / sentence_count) - 84.6 * (syllable_count / len(words))
    return round(max(min(score, 100.0), 0.0), 1)


def _reading_time_minutes(word_count):
    if word_count <= 0:
        return 0
    return max(1, math.ceil(word_count / 200))


def _extract_keywords(title, content, tags):
    counter = Counter()

    for word in _tokenize(content):
        normalized = _normalize_keyword(word)
        if len(normalized) >= 4 and normalized not in STOPWORDS:
            counter[normalized] += 1

    for word in _tokenize(title):
        normalized = _normalize_keyword(word)
        if len(normalized) >= 4 and normalized not in STOPWORDS:
            counter[normalized] += 2

    for word in _tokenize((tags or "").replace(",", " ")):
        normalized = _normalize_keyword(word)
        if len(normalized) >= 3 and normalized not in STOPWORDS:
            counter[normalized] += 3

    return [{"term": term, "count": count} for term, count in counter.most_common(5)]


def analyze_post_fields(title, content, meta_description="", tags="", category=""):
    title = (title or "").strip()
    content = (content or "").strip()
    meta_description = (meta_description or "").strip()
    tags = (tags or "").strip()
    category = (category or "").strip()

    words = _tokenize(content)
    word_count = len(words)
    sentence_count = _count_sentences(content)
    readability_score = _readability_score(content, words, sentence_count)
    reading_time_minutes = _reading_time_minutes(word_count)
    title_length = len(title)
    meta_length = len(meta_description)
    heading_lines = _heading_lines(content)
    heading_count = len(heading_lines)
    has_heading = heading_count > 0
    paragraph_count = len([paragraph for paragraph in re.split(r"\n\s*\n", content) if paragraph.strip()])

    keywords = _extract_keywords(title, content, tags)
    primary_keyword = keywords[0] if keywords else None
    primary_keyword_density = 0.0
    if primary_keyword and word_count:
        primary_keyword_density = round(primary_keyword["count"] / word_count * 100, 2)

    score = 0
    checks = []
    warnings = []
    suggestions = []

    def add_warning(message):
        if message not in warnings:
            warnings.append(message)

    def add_suggestion(message):
        if message not in suggestions:
            suggestions.append(message)

    if 30 <= title_length <= 60:
        score += 15
        checks.append({"label": "Title length", "status": "pass", "detail": "Title length is in a strong range."})
    elif title_length >= 20:
        score += 8
        add_warning("Adjust the title closer to 30 to 60 characters for a cleaner search snippet.")
        checks.append({"label": "Title length", "status": "warn", "detail": "Title is usable but not in the ideal range."})
    else:
        add_warning("The title is too short to communicate intent clearly.")
        add_suggestion("Expand the title with the main topic or reader outcome.")
        checks.append({"label": "Title length", "status": "fail", "detail": "Title needs more context."})

    if 120 <= meta_length <= 160:
        score += 10
        checks.append({"label": "Meta description", "status": "pass", "detail": "Meta description is in a good range."})
    elif meta_length >= 80:
        score += 5
        add_warning("Tighten the meta description toward 120 to 160 characters.")
        checks.append({"label": "Meta description", "status": "warn", "detail": "Meta description exists but could be tuned."})
    else:
        add_warning("Meta description is missing or too short.")
        add_suggestion("Write a meta description that summarizes the benefit of the post.")
        checks.append({"label": "Meta description", "status": "fail", "detail": "Meta description needs work."})

    if word_count >= 600:
        score += 20
        checks.append({"label": "Content depth", "status": "pass", "detail": "Content length is strong for an MVP blog post."})
    elif word_count >= 300:
        score += 14
        add_warning("The post has enough material to analyze, but more depth could strengthen it.")
        checks.append({"label": "Content depth", "status": "warn", "detail": "Content is acceptable but not especially deep."})
    elif word_count >= 150:
        score += 8
        add_warning("The post is still light on detail.")
        add_suggestion("Add another section with examples, steps, or takeaways.")
        checks.append({"label": "Content depth", "status": "warn", "detail": "Content is short for SEO-focused guidance."})
    else:
        add_warning("The content is too short for reliable SEO analysis.")
        add_suggestion("Add substantially more body content before publishing.")
        checks.append({"label": "Content depth", "status": "fail", "detail": "Content needs more substance."})

    if readability_score >= 60:
        score += 20
        checks.append({"label": "Readability", "status": "pass", "detail": "The writing should be approachable for a general audience."})
    elif readability_score >= 45:
        score += 12
        add_warning("The writing is somewhat dense.")
        add_suggestion("Shorten a few sentences and simplify complex phrasing.")
        checks.append({"label": "Readability", "status": "warn", "detail": "Readable, but on the dense side."})
    else:
        add_warning("Readability is low and may slow readers down.")
        add_suggestion("Break long sentences into shorter statements and simplify word choice.")
        checks.append({"label": "Readability", "status": "fail", "detail": "The copy is harder to scan than ideal."})

    if heading_count >= 2:
        score += 10
        checks.append({"label": "Heading structure", "status": "pass", "detail": "The draft includes multiple section headings."})
    elif has_heading:
        score += 6
        add_warning("Only one heading was detected, so the post may still feel flat to scan.")
        add_suggestion("Add another section heading to break the draft into clearer sections.")
        checks.append({"label": "Heading structure", "status": "warn", "detail": "The draft has some structure but could use more sections."})
    else:
        add_warning("No headings were detected in the body.")
        add_suggestion("Add section headings like `## Key Takeaways`, `Key Takeaways`, or HTML heading blocks to improve structure.")
        checks.append({"label": "Heading structure", "status": "fail", "detail": "The draft needs clearer section breaks."})

    if primary_keyword and 0.5 <= primary_keyword_density <= 3.0:
        score += 15
        checks.append({"label": "Keyword usage", "status": "pass", "detail": f"`{primary_keyword['term']}` appears naturally in the draft."})
    elif primary_keyword:
        score += 8
        add_warning(f"Primary keyword density for `{primary_keyword['term']}` is {primary_keyword_density}%.")
        add_suggestion("Keep the main keyword visible in the intro and a subheading without forcing repetition.")
        checks.append({"label": "Keyword usage", "status": "warn", "detail": "Keyword focus exists but could be better balanced."})
    else:
        add_warning("No strong keyword candidates were detected yet.")
        add_suggestion("Reinforce the main topic with more consistent vocabulary.")
        checks.append({"label": "Keyword usage", "status": "fail", "detail": "The draft lacks a clear keyword focus."})

    if paragraph_count >= 3:
        score += 10
        checks.append({"label": "Scannability", "status": "pass", "detail": "The draft has enough paragraph breaks for a long-form post."})
    else:
        add_warning("The draft would benefit from clearer section or paragraph breaks.")
        add_suggestion("Split dense blocks into shorter paragraphs to improve scanning.")
        checks.append({"label": "Scannability", "status": "fail", "detail": "Structure is still compact."})

    if not suggestions:
        add_suggestion("The draft is in good shape. Fine-tune the intro and internal links before publishing.")

    return {
        "seo_score": min(score, 100),
        "word_count": word_count,
        "readability_score": readability_score,
        "reading_time_minutes": reading_time_minutes,
        "sentence_count": sentence_count,
        "title_length": title_length,
        "meta_description_length": meta_length,
        "paragraph_count": paragraph_count,
        "heading_count": heading_count,
        "has_headings": has_heading,
        "keyword_candidates": keywords,
        "primary_keyword": primary_keyword["term"] if primary_keyword else None,
        "primary_keyword_density": primary_keyword_density,
        "warnings": warnings,
        "suggestions": suggestions,
        "checks": checks,
        "category": category,
        "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
    }


class SEOAnalyzer:
    def analyze(self, *, title, content, meta_description="", tags="", category=""):
        return analyze_post_fields(
            title=title,
            content=content,
            meta_description=meta_description,
            tags=tags,
            category=category,
        )


def analyze_post(*, title, content, meta_description="", tags="", category=""):
    return analyze_post_fields(
        title=title,
        content=content,
        meta_description=meta_description,
        tags=tags,
        category=category,
    )


def analyze_post_record(post):
    return analyze_post(
        title=post.title,
        content=post.content,
        meta_description=post.meta_description,
        tags=post.tags,
        category=post.category,
    )


def _report_payload(report):
    if report is None:
        return None

    suggestions_payload = {}
    if report.suggestions_json:
        try:
            suggestions_payload = json.loads(report.suggestions_json)
        except json.JSONDecodeError:
            suggestions_payload = {}

    if isinstance(suggestions_payload, list):
        suggestions_payload = {"suggestions": suggestions_payload}

    keywords = []
    if report.keywords_json:
        try:
            keywords = json.loads(report.keywords_json)
        except json.JSONDecodeError:
            keywords = []

    normalized_keywords = []
    for keyword in keywords:
        if isinstance(keyword, dict):
            normalized_keywords.append(keyword)
        else:
            normalized_keywords.append({"term": str(keyword), "count": None})

    internal_links = []
    if report.internal_links_json:
        try:
            internal_links = json.loads(report.internal_links_json)
        except json.JSONDecodeError:
            internal_links = []

    return {
        "report_id": report.id,
        "created_at": report.created_at,
        "seo_score": report.seo_score,
        "word_count": report.word_count,
        "readability_score": report.readability_score,
        "keyword_candidates": normalized_keywords,
        "warnings": suggestions_payload.get("warnings", []),
        "suggestions": suggestions_payload.get("suggestions", []),
        "checks": suggestions_payload.get("checks", []),
        "reading_time_minutes": suggestions_payload.get("reading_time_minutes"),
        "sentence_count": suggestions_payload.get("sentence_count"),
        "title_length": suggestions_payload.get("title_length"),
        "meta_description_length": suggestions_payload.get("meta_description_length"),
        "paragraph_count": suggestions_payload.get("paragraph_count"),
        "heading_count": suggestions_payload.get("heading_count"),
        "has_headings": suggestions_payload.get("has_headings"),
        "primary_keyword": suggestions_payload.get("primary_keyword"),
        "primary_keyword_density": suggestions_payload.get("primary_keyword_density"),
        "keyword_density": {},
        "repeated_terms": [],
        "internal_links": internal_links,
    }


def serialize_report(report):
    return _report_payload(report)


def deserialize_seo_report(report):
    return _report_payload(report)


def get_latest_seo_report(post):
    return (
        SEOReport.query.filter_by(post_id=post.id)
        .order_by(SEOReport.created_at.desc(), SEOReport.id.desc())
        .first()
    )


def get_latest_post_analysis(post):
    return serialize_report(get_latest_seo_report(post))


def save_seo_report(post, analysis, *, internal_links=None):
    report = SEOReport(
        post=post,
        word_count=analysis.get("word_count"),
        readability_score=analysis.get("readability_score"),
        seo_score=analysis.get("seo_score"),
        suggestions_json=json.dumps(
            {
                "suggestions": analysis.get("suggestions", []),
                "warnings": analysis.get("warnings", []),
                "checks": analysis.get("checks", []),
                "reading_time_minutes": analysis.get("reading_time_minutes"),
                "sentence_count": analysis.get("sentence_count"),
                "title_length": analysis.get("title_length"),
                "meta_description_length": analysis.get("meta_description_length"),
                "paragraph_count": analysis.get("paragraph_count"),
                "heading_count": analysis.get("heading_count"),
                "has_headings": analysis.get("has_headings"),
                "primary_keyword": analysis.get("primary_keyword"),
                "primary_keyword_density": analysis.get("primary_keyword_density"),
            }
        ),
        keywords_json=json.dumps(analysis.get("keyword_candidates", [])),
        internal_links_json=json.dumps(internal_links or []),
    )
    db.session.add(report)
    return report


def save_post_analysis(post, analysis, *, internal_links=None):
    report = save_seo_report(post, analysis, internal_links=internal_links)
    db.session.commit()
    return report

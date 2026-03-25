import json
import re
from collections import Counter

from app import db
from app.models import SEOReport

try:
    import textstat
except ImportError:  # pragma: no cover - fallback path is intentionally supported
    textstat = None


STOP_WORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "like",
    "make",
    "more",
    "most",
    "need",
    "not",
    "of",
    "often",
    "on",
    "or",
    "our",
    "out",
    "page",
    "post",
    "posts",
    "search",
    "should",
    "site",
    "small",
    "so",
    "some",
    "such",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "they",
    "this",
    "to",
    "too",
    "use",
    "useful",
    "using",
    "very",
    "was",
    "way",
    "we",
    "well",
    "what",
    "when",
    "whether",
    "which",
    "while",
    "will",
    "with",
    "without",
    "work",
    "writer",
    "writers",
    "writing",
    "you",
    "your",
}

WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]+")
HTML_HEADING_PATTERN = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _clean_text(value):
    return (value or "").strip()


def _tokenize(text):
    return [token.lower() for token in WORD_PATTERN.findall(text)]


def _split_sentences(text):
    stripped = _clean_text(text)
    if not stripped:
        return []

    parts = re.split(r"(?<=[.!?])\s+", stripped)
    return [part.strip() for part in parts if part.strip()]


def _split_paragraphs(text):
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text or "") if paragraph.strip()]


def _estimate_syllables(word):
    token = re.sub(r"[^a-z]", "", word.lower())
    if not token:
        return 0

    groups = re.findall(r"[aeiouy]+", token)
    syllables = len(groups)
    if token.endswith("e") and syllables > 1:
        syllables -= 1
    return max(1, syllables)


def _fallback_flesch_reading_ease(text):
    words = _tokenize(text)
    sentences = _split_sentences(text)
    if not words or not sentences:
        return None

    syllable_count = sum(_estimate_syllables(word) for word in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllable_count / len(words)
    return round(206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word), 2)


def _extract_headings(content):
    headings = []

    for match in HTML_HEADING_PATTERN.finditer(content or ""):
        headings.append({"level": int(match.group(1)), "text": re.sub(r"<[^>]+>", "", match.group(2)).strip()})

    for match in MARKDOWN_HEADING_PATTERN.finditer(content or ""):
        headings.append({"level": len(match.group(1)), "text": match.group(2).strip()})

    return headings


class SEOAnalyzer:
    SCORE_WEIGHTS = {
        "title": 15,
        "meta_description": 15,
        "content_length": 20,
        "readability": 20,
        "heading_structure": 10,
        "keyword_usage": 20,
    }

    def analyze(
        self,
        *,
        title,
        content,
        meta_description="",
        tags="",
        category="",
    ):
        title = _clean_text(title)
        content = _clean_text(content)
        meta_description = _clean_text(meta_description)
        tags = _clean_text(tags)
        category = _clean_text(category)

        words = _tokenize(content)
        word_count = len(words)
        sentence_list = _split_sentences(content)
        sentence_count = len(sentence_list)
        paragraph_list = _split_paragraphs(content)
        paragraph_count = len(paragraph_list)
        headings = _extract_headings(content)
        estimated_reading_time = round(word_count / 200, 1) if word_count else 0.0
        readability_score = self._readability_score(content)

        keyword_data = self._keyword_analysis(
            title=title,
            content=content,
            tags=tags,
            category=category,
            word_count=word_count,
        )
        title_checks = self._title_checks(title)
        meta_checks = self._meta_checks(meta_description)
        heading_checks = self._heading_checks(headings, paragraph_count)
        content_checks = self._content_checks(word_count, sentence_count, paragraph_count)
        readability_checks = self._readability_checks(readability_score)
        keyword_checks = self._keyword_checks(keyword_data, word_count)

        scored_sections = {
            "title": title_checks["score"],
            "meta_description": meta_checks["score"],
            "content_length": content_checks["score"],
            "readability": readability_checks["score"],
            "heading_structure": heading_checks["score"],
            "keyword_usage": keyword_checks["score"],
        }

        seo_score = round(sum(scored_sections.values()))
        suggestions = self._prioritize_suggestions(
            title_checks["suggestions"]
            + meta_checks["suggestions"]
            + content_checks["suggestions"]
            + readability_checks["suggestions"]
            + heading_checks["suggestions"]
            + keyword_checks["suggestions"]
        )

        warnings = [
            item["message"]
            for item in suggestions
            if item["priority"] in {"high", "medium"}
        ]
        passed_checks = [
            check
            for collection in (
                title_checks["passed_checks"],
                meta_checks["passed_checks"],
                content_checks["passed_checks"],
                readability_checks["passed_checks"],
                heading_checks["passed_checks"],
                keyword_checks["passed_checks"],
            )
            for check in collection
        ]

        return {
            "seo_score": _clamp(seo_score, 0, 100),
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "readability_score": readability_score,
            "estimated_reading_time_minutes": estimated_reading_time,
            "keyword_candidates": keyword_data["keyword_candidates"],
            "keyword_density": keyword_data["keyword_density"],
            "repeated_terms": keyword_data["repeated_terms"],
            "primary_keyword": keyword_data["primary_keyword"],
            "title_checks": self._serialize_check_result(title_checks, "title"),
            "meta_description_checks": self._serialize_check_result(meta_checks, "meta_description"),
            "heading_structure_checks": self._serialize_check_result(heading_checks, "heading_structure"),
            "content_checks": self._serialize_check_result(content_checks, "content_length"),
            "readability_checks": self._serialize_check_result(readability_checks, "readability"),
            "keyword_checks": self._serialize_check_result(keyword_checks, "keyword_usage"),
            "headings": headings,
            "suggestions": suggestions,
            "warnings": warnings,
            "passed_checks": passed_checks,
            "scoring_breakdown": {
                key: {
                    "score": value,
                    "max_score": self.SCORE_WEIGHTS[key],
                }
                for key, value in scored_sections.items()
            },
            "notes": [
                "This score is based on on-page content quality heuristics only.",
                "The analyzer does not estimate live rankings, keyword competitiveness, or search volume.",
            ],
        }

    def _readability_score(self, content):
        if not content:
            return None

        if textstat is not None:
            return round(textstat.flesch_reading_ease(content), 2)

        return _fallback_flesch_reading_ease(content)

    def _title_checks(self, title):
        score = 0
        suggestions = []
        passed_checks = []
        title_length = len(title)

        if 45 <= title_length <= 65:
            score += 15
            passed_checks.append("Title length is within a strong SEO-friendly range.")
        elif 35 <= title_length <= 75:
            score += 10
            suggestions.append(self._suggestion("medium", "title", "Tighten the title to roughly 45-65 characters for better scanability."))
        elif title_length == 0:
            suggestions.append(self._suggestion("high", "title", "Add a clear title before running SEO analysis."))
        else:
            score += 5
            suggestions.append(self._suggestion("high", "title", "Rewrite the title so it is concise and specific, ideally around 45-65 characters."))

        if ":" in title or "-" in title:
            passed_checks.append("Title uses a descriptive separator that can improve clarity.")

        return {
            "score": score,
            "passed_checks": passed_checks,
            "suggestions": suggestions,
            "details": {"length": title_length},
        }

    def _meta_checks(self, meta_description):
        score = 0
        suggestions = []
        passed_checks = []
        meta_length = len(meta_description)

        if 120 <= meta_length <= 160:
            score = 15
            passed_checks.append("Meta description length is strong for a search snippet.")
        elif 90 <= meta_length <= 175:
            score = 10
            suggestions.append(self._suggestion("medium", "meta_description", "Refine the meta description toward 120-160 characters for a tighter summary."))
        elif meta_length == 0:
            suggestions.append(self._suggestion("high", "meta_description", "Add a meta description that explains the reader benefit in one or two sentences."))
        else:
            score = 5
            suggestions.append(self._suggestion("high", "meta_description", "Rewrite the meta description so it clearly summarizes the page in about 120-160 characters."))

        return {
            "score": score,
            "passed_checks": passed_checks,
            "suggestions": suggestions,
            "details": {"length": meta_length},
        }

    def _content_checks(self, word_count, sentence_count, paragraph_count):
        score = 0
        suggestions = []
        passed_checks = []

        if word_count >= 900:
            score += 20
            passed_checks.append("Content length is strong enough to cover a topic in depth.")
        elif word_count >= 600:
            score += 14
            suggestions.append(self._suggestion("medium", "content_length", "Expand the article with a few more concrete examples or explanations to strengthen topical depth."))
        elif word_count >= 300:
            score += 8
            suggestions.append(self._suggestion("high", "content_length", "The article is light for SEO analysis. Add more depth, examples, or supporting sections."))
        else:
            suggestions.append(self._suggestion("high", "content_length", "Content is too short for a strong SEO result. Add substantially more useful body content."))

        if sentence_count >= 5:
            passed_checks.append("Content has enough sentence structure for readability analysis.")
        else:
            suggestions.append(self._suggestion("medium", "content_length", "Break the content into more complete sentences so the page reads like a developed article."))

        if paragraph_count >= 3:
            passed_checks.append("Content is divided into scan-friendly paragraphs.")
        else:
            suggestions.append(self._suggestion("medium", "content_length", "Split the content into multiple paragraphs to improve scanability."))

        return {
            "score": score,
            "passed_checks": passed_checks,
            "suggestions": suggestions,
            "details": {
                "word_count": word_count,
                "sentence_count": sentence_count,
                "paragraph_count": paragraph_count,
            },
        }

    def _readability_checks(self, readability_score):
        score = 0
        suggestions = []
        passed_checks = []

        if readability_score is None:
            suggestions.append(self._suggestion("medium", "readability", "Readability could not be calculated because the content is too thin or malformed."))
        elif readability_score >= 60:
            score = 20
            passed_checks.append("Readability is in a strong range for general web content.")
        elif readability_score >= 45:
            score = 14
            suggestions.append(self._suggestion("medium", "readability", "Simplify a few long sentences to push readability into a more accessible range."))
        elif readability_score >= 30:
            score = 8
            suggestions.append(self._suggestion("high", "readability", "The draft is difficult to scan. Shorten sentences and replace dense phrasing with clearer language."))
        else:
            score = 4
            suggestions.append(self._suggestion("high", "readability", "Readability is very low. Rewrite for shorter sentences, simpler transitions, and clearer wording."))

        return {
            "score": score,
            "passed_checks": passed_checks,
            "suggestions": suggestions,
            "details": {"readability_score": readability_score},
        }

    def _heading_checks(self, headings, paragraph_count):
        score = 0
        suggestions = []
        passed_checks = []
        heading_levels = [heading["level"] for heading in headings]

        if headings:
            score += 6
            passed_checks.append("The draft includes headings that can improve scanability.")
        elif paragraph_count >= 4:
            suggestions.append(self._suggestion("high", "heading_structure", "Add section headings so longer content is easier to scan and understand."))
        else:
            suggestions.append(self._suggestion("medium", "heading_structure", "Consider adding headings as the article grows to clarify its structure."))

        if heading_levels and 1 in heading_levels:
            score += 2
            passed_checks.append("The heading structure includes a top-level heading.")
        elif heading_levels:
            suggestions.append(self._suggestion("low", "heading_structure", "Start the heading outline with an H1-style heading to anchor the article structure."))

        if heading_levels and heading_levels == sorted(heading_levels):
            score += 2
            passed_checks.append("Heading levels appear in a logical order.")
        elif len(heading_levels) > 1:
            suggestions.append(self._suggestion("medium", "heading_structure", "Keep heading levels in a logical order without jumping abruptly between levels."))

        return {
            "score": score,
            "passed_checks": passed_checks,
            "suggestions": suggestions,
            "details": {"heading_count": len(headings), "levels": heading_levels},
        }

    def _keyword_analysis(self, *, title, content, tags, category, word_count):
        tokens = _tokenize(content)
        filtered_tokens = [token for token in tokens if len(token) >= 3 and token not in STOP_WORDS]
        counts = Counter(filtered_tokens)

        keyword_candidates = []
        for keyword, count in counts.most_common(8):
            density = round((count / word_count) * 100, 2) if word_count else 0.0
            keyword_candidates.append({"keyword": keyword, "count": count, "density": density})

        primary_keyword = keyword_candidates[0]["keyword"] if keyword_candidates else None
        keyword_density = {
            item["keyword"]: item["density"]
            for item in keyword_candidates[:5]
        }
        repeated_terms = [item for item in keyword_candidates if item["count"] >= 3]

        context_terms = {
            token
            for token in _tokenize(" ".join(part for part in (title, tags, category) if part))
            if len(token) >= 3 and token not in STOP_WORDS
        }

        return {
            "keyword_candidates": keyword_candidates,
            "keyword_density": keyword_density,
            "repeated_terms": repeated_terms,
            "primary_keyword": primary_keyword,
            "context_terms": sorted(context_terms),
        }

    def _keyword_checks(self, keyword_data, word_count):
        score = 0
        suggestions = []
        passed_checks = []
        keyword_candidates = keyword_data["keyword_candidates"]
        context_terms = set(keyword_data["context_terms"])
        primary_keyword = keyword_data["primary_keyword"]

        if keyword_candidates:
            score += 8
            passed_checks.append("The article has repeated topical terms that can anchor keyword guidance.")
        else:
            suggestions.append(self._suggestion("high", "keyword_usage", "The content does not repeat any meaningful topical terms yet. Strengthen the main theme with clearer, consistent language."))

        if primary_keyword:
            primary_density = keyword_data["keyword_density"].get(primary_keyword, 0.0)
            if 0.5 <= primary_density <= 2.5:
                score += 8
                passed_checks.append("Primary keyword repetition is present without looking excessive.")
            elif primary_density > 2.5:
                score += 3
                suggestions.append(self._suggestion("high", "keyword_usage", f'The term "{primary_keyword}" appears heavily. Reduce repetition and use natural variations.'))
            else:
                score += 4
                suggestions.append(self._suggestion("medium", "keyword_usage", f'Use the main topic term "{primary_keyword}" a little more consistently in key sections if it fits naturally.'))

        if context_terms and any(term in {item["keyword"] for item in keyword_candidates[:5]} for term in context_terms):
            score += 4
            passed_checks.append("Content language overlaps with the title, tags, or category.")
        elif word_count:
            suggestions.append(self._suggestion("medium", "keyword_usage", "Align body copy more closely with the title, tags, or category so the topic stays explicit."))

        return {
            "score": score,
            "passed_checks": passed_checks,
            "suggestions": suggestions,
            "details": {
                "primary_keyword": primary_keyword,
                "context_terms": sorted(context_terms),
            },
        }

    def _serialize_check_result(self, result, key):
        return {
            "score": result["score"],
            "max_score": self.SCORE_WEIGHTS[key],
            "details": result["details"],
        }

    def _prioritize_suggestions(self, suggestions):
        priority_order = {"high": 0, "medium": 1, "low": 2}
        ordered = sorted(
            suggestions,
            key=lambda item: (priority_order[item["priority"]], item["category"], item["message"]),
        )
        return ordered

    def _suggestion(self, priority, category, message):
        return {"priority": priority, "category": category, "message": message}


def analyze_post(*, title, content, meta_description="", tags="", category=""):
    analyzer = SEOAnalyzer()
    return analyzer.analyze(
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


def get_latest_seo_report(post):
    return (
        SEOReport.query.filter_by(post_id=post.id)
        .order_by(SEOReport.created_at.desc(), SEOReport.id.desc())
        .first()
    )


def deserialize_seo_report(report):
    if report is None:
        return None

    suggestions = json.loads(report.suggestions_json or "[]")
    keyword_payload = json.loads(report.keywords_json or "{}")
    internal_links = json.loads(report.internal_links_json or "[]")

    return {
        "report_id": report.id,
        "created_at": report.created_at,
        "word_count": report.word_count,
        "readability_score": report.readability_score,
        "seo_score": report.seo_score,
        "suggestions": suggestions,
        "keyword_candidates": keyword_payload.get("keyword_candidates", []),
        "keyword_density": keyword_payload.get("keyword_density", {}),
        "repeated_terms": keyword_payload.get("repeated_terms", []),
        "primary_keyword": keyword_payload.get("primary_keyword"),
        "internal_links": internal_links,
    }


def save_seo_report(post, analysis, *, internal_links=None):
    report = SEOReport(
        post=post,
        word_count=analysis.get("word_count"),
        readability_score=analysis.get("readability_score"),
        seo_score=analysis.get("seo_score"),
        suggestions_json=json.dumps(analysis.get("suggestions", [])),
        keywords_json=json.dumps(
            {
                "primary_keyword": analysis.get("primary_keyword"),
                "keyword_candidates": analysis.get("keyword_candidates", []),
                "keyword_density": analysis.get("keyword_density", {}),
                "repeated_terms": analysis.get("repeated_terms", []),
            }
        ),
        internal_links_json=json.dumps(internal_links or []),
    )
    db.session.add(report)
    return report

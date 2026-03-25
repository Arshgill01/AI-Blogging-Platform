---
name: seo-analysis
description: Use this skill when implementing or improving the SEO analysis pipeline for blog posts, including readability, keyword extraction, scoring, and actionable suggestions.
---

# SEO Analysis

## Purpose

This skill implements the author-side intelligence layer that analyzes a blog post and returns SEO-focused feedback.

Use this skill when the task involves:

- keyword extraction
- readability scoring
- SEO scoring
- content quality checks
- author suggestions UI
- SEO report generation/storage

This platform does not depend on external SEO APIs.
The SEO system must be self-contained and explainable.

---

## Product role

The SEO analyzer helps authors improve a post before publishing.

It should analyze:

- title
- content
- meta description
- headings
- keyword usage
- content length
- internal link opportunities

It should return:

- a score
- specific suggestions
- keyword insights
- machine-readable output for display or storage

---

## Design philosophy

Favor:

- deterministic logic
- rule-based checks
- lightweight NLP
- transparent scoring

Do not build a fake enterprise SEO engine.
Build a credible, understandable MVP.

---

## Recommended tools

Good options include:

- textstat for readability
- Python regex / string parsing for heading checks
- collections.Counter for frequency analysis
- optional lightweight keyword extraction such as YAKE or a simple TF-IDF-based approach

Keep dependencies minimal unless a library provides strong value.

---

## Expected analysis outputs

### Basic metrics

- word count
- sentence count if easy
- readability score
- estimated reading time if useful

### Structural checks

- title length
- meta description presence/length
- heading presence / heading structure
- paragraph health if easy

### Keyword analysis

- top keyword candidates
- density summary
- repeated terms of interest
- keyword overuse / underuse hints

### Suggestions

Examples:

- title too short
- meta description missing
- readability too difficult
- content too short
- insufficient structure/headings
- keyword repetition weak or excessive
- add relevant internal links

### Final score

Return a simple normalized score, for example out of 100.

---

## Suggested scoring approach

Keep it easy to tune.

For example:

- title quality: 15
- meta description: 10
- content length: 15
- readability: 20
- heading structure: 10
- keyword usage: 20
- internal linking opportunity: 10

This does not need to be exact.
It needs to be consistent and explainable.

---

## Implementation guidance

### Input

Typically analyze:

- post title
- post content
- post meta description
- maybe category/tags if helpful

### Output shape

Prefer a structured dictionary/object with fields like:

- seo_score
- word_count
- readability_score
- keyword_candidates
- keyword_density
- suggestions
- passed_checks
- warnings

### Storage

If the app already supports SEOReport, optionally store the analysis result.

---

## UI expectations

The author should be able to clearly see:

- SEO score
- major warnings
- prioritized suggestions
- top keyword candidates
- internal link opportunities if already available

The UI should help the user act on the feedback.

---

## Constraints

Do not:

- call external SEO services
- scrape search engines
- pretend to know real SERP rankings
- make claims the system cannot support

This is an internal SEO guidance engine, not a live Google optimizer.

---

## Working style

When using this skill:

1. Start with a robust, simple analyzer.
2. Make the output readable for humans and machines.
3. Handle empty or messy input gracefully.
4. Avoid fragile NLP pipelines that require large downloads unless essential.

---

## Definition of done

This skill is successful when:

- a post can be analyzed reliably
- an SEO score is produced
- suggestions are actionable
- output is renderable in the app UI
- the logic is understandable and defensible in a demo

---

## Coordination notes

This skill should integrate cleanly with:

- post models
- author create/edit flow
- similarity/internal linking service
- analytics/dashboard if score snapshots are displayed

---
name: content-similarity
description: Use this skill when implementing semantic relatedness between posts, internal link suggestions, and related-content ranking using TF-IDF and cosine similarity.
---

# Content Similarity

## Purpose

This skill implements the internal content retrieval layer of the blogging platform.

Use this skill when the task involves:

- related posts
- internal link suggestions
- semantic similarity between blog posts
- TF-IDF vectorization
- cosine similarity ranking

All related-content logic must use posts already stored inside the platform.

---

## Product role

This subsystem serves two major use cases:

### 1. Author-side internal link suggestions

When an author writes or edits a post, the system should recommend 3–5 related posts that could be linked internally.

### 2. Reader-side related posts

When a reader views a post, the system can show similar articles to deepen engagement.

---

## Design philosophy

Use classical information retrieval.
Prefer:

- TF-IDF vectorization
- cosine similarity
- explainable ranking

This is the correct level of sophistication for the project deadline and product scope.

Do not overcomplicate this with heavy embeddings unless explicitly required.

---

## Recommended approach

### Text representation

Represent each post using a text field built from:

- title
- content
- category
- tags if useful

### Similarity engine

- vectorize posts with TF-IDF
- vectorize current target text
- compute cosine similarity
- exclude the current post
- return top ranked matches

This should be fast, deterministic, and easy to inspect.

---

## Expected outputs

For a given post, return:

- top related post IDs
- titles
- optional similarity scores
- optional short explanation or anchor text hint if easy

Keep the API simple and reusable.

---

## Relevance heuristics

In addition to raw similarity, you may lightly improve ranking by considering:

- category match
- tag overlap
- recency boost
- minimum content quality thresholds

But keep TF-IDF + cosine as the backbone.

---

## Good implementation choices

Prefer:

- a reusable service function/class
- explicit exclusion of self
- handling low-data cases gracefully
- sensible defaults for top N results

For example:

- if fewer than 3 alternative posts exist, return fewer
- avoid crashing on tiny or empty corpora

---

## Integration targets

This skill should integrate with:

- author SEO analysis view
- post detail page
- recommendation engine if it uses content similarity as a signal

---

## Constraints

Do not:

- fetch web content
- depend on external search engines
- build a massive indexing layer
- introduce infrastructure that is unnecessary for the local demo

This is an internal retrieval engine for a self-contained platform.

---

## Working style

When using this skill:

1. Keep the implementation compact and reliable.
2. Use clean input/output boundaries.
3. Write code that another agent can call from personalization or SEO flows.
4. Validate results qualitatively with seeded sample posts.

---

## Definition of done

This skill is successful when:

- the system can compute related posts
- self-matches are excluded
- obviously relevant posts tend to rank above obviously irrelevant ones
- the output is integrated into author and/or reader flows

---

## Coordination notes

This skill should not own:

- session tracking
- dashboard metrics
- SEO scoring itself

It should focus on reusable content similarity and internal linking logic.

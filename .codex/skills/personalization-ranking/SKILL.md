---
name: personalization-ranking
description: Use this skill when implementing visitor tracking, preference estimation, and personalized recommendation ranking based on in-platform behavior.
---

# Personalization Ranking

## Purpose

This skill implements reader-side personalization for the blogging platform.

Use this skill when the task involves:

- session tracking
- interaction logging
- user interest estimation
- personalized recommendations
- behavior-based ranking

This system must remain self-contained.
All personalization should come from in-platform reading behavior and platform content.

---

## Product role

When a reader browses posts, the platform should adapt recommended content based on signals such as:

- categories viewed
- recent posts read
- dwell time
- clicked recommendations
- overall content similarity
- small popularity signals

The goal is to increase engagement in a believable, explainable way.

---

## Design philosophy

Prefer:

- lightweight behavioral modeling
- rule-based weighted scoring
- explainable recommendation logic

Do not build or pretend to build a heavy recommender model.
This is a practical MVP recommender.

---

## Key concepts

### Session identity

Use a simple session token stored in cookie/session state or similar.
This is enough for the project.
Avoid full auth complexity unless explicitly required.

### Behavior signals

Track:

- post views
- categories viewed
- dwell time
- recommendation clicks
- recent reading history

### Candidate generation

Candidate posts should come from:

- all posts excluding already viewed ones
- optionally a filtered subset such as same-category or similar posts

### Ranking

Use a weighted formula such as:

```text
score =
0.35 * category_preference
+ 0.30 * semantic_similarity
+ 0.20 * popularity_score
+ 0.10 * recency_score
+ 0.05 * dwell_time_affinity
```

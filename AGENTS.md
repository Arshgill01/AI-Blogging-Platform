# AGENTS.md

## Project

AI-Powered Blogging Platform

## Mission

Build a self-contained blogging platform with two sides:

1. Author side

- create and edit blog posts
- run SEO analysis
- receive internal link suggestions

2. Reader side

- browse and read blog posts
- receive personalized recommendations

The platform must use only its own stored content and in-platform user behavior.
No internet scraping. No external recommendation sources. No external blogging engines.

---

## Product goals

The final MVP should demonstrate:

- blog creation and viewing
- SEO analysis for posts
- internal link suggestions based on content similarity
- reader personalization based on session behavior
- analytics dashboard
- seeded content for a believable demo

---

## Non-goals

Do not spend time on:

- full article generation
- external search engine integration
- live web scraping
- production deployment complexity
- advanced auth unless required by the current implementation
- deep learning training pipelines
- enterprise-scale architecture

---

## Stack

Preferred stack unless a strong implementation reason requires otherwise:

- Flask
- SQLite
- SQLAlchemy
- Jinja templates
- Bootstrap
- Chart.js
- scikit-learn
- textstat
- optional: nltk / yake

---

## Architecture principles

### 1. Keep the app self-contained

All recommendation, personalization, and internal linking logic must operate on posts stored inside the platform.

### 2. Favor explainable intelligence

Use:

- rule-based SEO checks
- TF-IDF + cosine similarity
- behavior-based ranking

Avoid black-box complexity where simple, explainable methods are sufficient.

### 3. Ship a credible MVP

A complete, coherent MVP is better than a half-built ambitious system.

### 4. Respect module boundaries

Each subsystem should be implemented with clear ownership and minimal cross-file thrashing.

### 5. Seed data is part of the product

The app must include enough sample posts and interactions to make the demo convincing.

---

## Core subsystems

### A. Content subsystem

Responsible for:

- post creation
- post editing
- post listing and viewing
- categories and tags
- sample seed data

### B. SEO subsystem

Responsible for:

- word count
- readability
- keyword candidate extraction
- title/meta/heading checks
- SEO score
- SEO suggestions

### C. Similarity subsystem

Responsible for:

- content vectorization
- related post detection
- internal link suggestions

### D. Personalization subsystem

Responsible for:

- session tracking
- interaction logging
- preference estimation
- personalized recommendation ranking

### E. Analytics subsystem

Responsible for:

- aggregating reader behavior
- post-level metrics
- category-level metrics
- dashboard data

---

## Recommended folder shape

This is a suggested shape, not a hard constraint, but keep things organized.

\`\`\`
app/
**init**.py
models.py
routes/
main.py
posts.py
analytics.py
services/
seo_service.py
similarity_service.py
personalization_service.py
analytics_service.py
templates/
static/
seed.py
run.py
requirements.txt
README.md
\`\`\`

---

## Data model expectations

### Post

Fields should support:

- id
- title
- content
- category
- tags
- meta_description
- created_at
- updated_at

### VisitorSession

Fields should support:

- id
- session_token
- first_seen
- last_seen

### Interaction

Fields should support:

- id
- session_token
- post_id
- event_type
- dwell_time
- timestamp

### SEOReport

Fields should support:

- id
- post_id
- word_count
- readability_score
- seo_score
- suggestions_json
- keywords_json
- internal_links_json
- created_at

---

## Intelligence design

### SEO analysis

Should be lightweight and explainable.

Expected checks:

- title length
- meta description presence/length
- heading structure
- readability
- keyword repetition / density
- content length
- internal linking opportunities

Output should include:

- overall score
- prioritized suggestions
- extracted keyword candidates
- machine-readable data for dashboard or display

### Internal link suggestions

Should be based on:

- TF-IDF representation of current post and existing posts
- cosine similarity ranking
- top 3–5 related posts

### Personalization

Should be based on:

- viewed categories
- clicked recommendations
- dwell time
- recent reading behavior
- small popularity boost
- penalty for already-viewed content

Use a weighted ranking formula.
Keep it easy to understand and tune.

---

## Parallel execution rules

### Rule 1

Do not refactor unrelated modules while implementing your task.

### Rule 2

Do not introduce framework migrations unless clearly necessary.

### Rule 3

If touching shared files, keep changes minimal and well-scoped.

### Rule 4

Prefer additive changes over sweeping rewrites.

### Rule 5

Every branch should leave the app in a runnable state.

---

## Branch ownership model

### Agent 1 — Foundation / App skeleton

Owns:

- Flask app setup
- database initialization
- base templates
- model scaffolding
- seed setup
- primary routes skeleton

### Agent 2 — SEO subsystem

Owns:

- SEO service
- keyword extraction
- readability analysis
- SEO scoring logic
- author-side analysis UI integration

### Agent 3 — Similarity subsystem

Owns:

- TF-IDF indexing
- cosine similarity
- related posts logic
- internal link suggestions

### Agent 4 — Personalization + analytics

Owns:

- session tracking
- interaction logging
- recommendation ranking
- analytics aggregation
- dashboard metrics

### Agent 5 — Integration / polish

Owns:

- UI cleanup
- cross-module integration fixes
- demo readiness
- README/demo instructions
- seed quality improvement

---

## Quality bar

A feature is done when:

- it works locally
- it is integrated into the UI or route flow
- it does not break existing flows
- it is understandable from code alone
- it has at least basic validation or guardrails
- it is demoable

---

## Testing expectations

At minimum, contributors should verify:

- app boots successfully
- database initializes
- seed data loads
- posts can be viewed
- SEO analysis returns valid output
- related posts are shown
- recommendation logic returns sensible output
- dashboard renders without crashing

If time allows, add lightweight tests for core services.

---

## UX expectations

The UI does not need to be fancy, but it must be coherent.

Expected visible pages:

- homepage / post listing
- post detail page
- author create/edit page
- SEO results display
- personalized recommendations area
- dashboard page

---

## Demo expectations

The final app should support this sequence:

1. Create or open a blog post
2. Show SEO analysis and suggestions
3. Show internal link suggestions
4. Browse posts as a reader
5. Show recommendations adapting to reading behavior
6. Open dashboard and show engagement metrics

---

## Decision rule under time pressure

When in doubt, choose:

- simpler
- more explainable
- more stable
- faster to demo

Do not chase unnecessary sophistication.

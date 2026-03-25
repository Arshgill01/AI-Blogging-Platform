# PLAN.md

## Project

AI-Powered Blogging Platform

## Deadline strategy

We have limited time.
The goal is to build the strongest believable MVP, not the most ambitious system.

This plan prioritizes:

- coherence
- demoability
- fast implementation
- explainable intelligence
- parallel execution

---

# 1. Final product definition

Build a self-contained blogging platform where:

## Author side

- authors create and edit posts
- the platform analyzes posts for SEO quality
- the platform suggests internal links from existing stored posts

## Reader side

- readers browse and read posts
- the platform tracks behavior using session-based history
- the platform recommends posts based on interest and similarity

## Admin side

- dashboard shows engagement and content metrics

All intelligence is derived from:

- platform content
- platform interactions
- built-in heuristic logic

Not from the open internet.

---

# 2. Locked scope

## Included

- post CRUD or at least create + view + edit
- categories and tags
- SEO analyzer
- internal link suggestions
- session-based personalization
- recommendation ranking
- analytics dashboard
- seed data

## Excluded

- internet scraping
- external SEO APIs
- external recommendation systems
- full article generation
- complex auth
- advanced admin permissions
- model training pipelines
- deployment complexity beyond local demo readiness

---

# 3. Technical design

## Backend

Flask app with modular services.

## Database

SQLite with SQLAlchemy models.

## Templates

Jinja templates with Bootstrap.

## Charts

Chart.js for dashboard visualizations.

## NLP / IR techniques

- keyword extraction
- readability analysis
- TF-IDF vectorization
- cosine similarity
- weighted rule-based recommendation ranking

---

# 4. High-level architecture

\`\`\`
UI Layer

- Author pages
- Reader pages
- Dashboard

Application Layer

- routes
- services
- models

Intelligence Layer

- SEO analysis
- similarity engine
- personalization engine
- analytics aggregation

Persistence Layer

- posts
- sessions
- interactions
- seo reports
  \`\`\`

---

# 5. Feature details

## 5.1 Content system

### Required

- create a post
- edit a post
- list posts
- view a post
- store category/tags/meta description

### Nice if easy

- delete post
- draft/published flag

---

## 5.2 SEO analyzer

### Inputs

- title
- content
- meta description
- category/tags if useful

### Outputs

- word count
- readability score
- candidate keywords
- keyword density summary
- warnings
- suggestions
- overall SEO score

### Suggested rules

- title too short / too long
- missing meta description
- weak content length
- poor readability
- missing headings
- overused or underused target keywords
- no related internal link opportunities

---

## 5.3 Internal linking engine

### Goal

Suggest 3–5 relevant internal posts for the current post.

### Method

- vectorize all posts with TF-IDF
- vectorize current post
- compute cosine similarity
- rank candidates
- return top matches excluding self

### Output

- related post titles
- maybe similarity score
- suitable anchor text hint if easy

---

## 5.4 Personalization engine

### Goal

Rank recommended posts for a reader using in-platform behavior.

### Signals

- categories viewed
- recent posts viewed
- time spent
- recommendation clicks
- overall popularity
- recency
- content similarity to recent reads

### Candidate ranking idea

\`\`\`
score =
0.35 \* category_preference

- 0.30 \* semantic_similarity
- 0.20 \* popularity_score
- 0.10 \* recency_score
- 0.05 \* dwell_time_affinity
  \`\`\`

Penalize:

- already viewed posts

### Output

- ranked recommended posts list

---

## 5.5 Analytics dashboard

### Show at least

- total posts
- total interactions
- most viewed posts
- category popularity
- average dwell time
- recommendation click count
- SEO score snapshots by post

### Nice if easy

- trend charts
- top recommended categories
- engagement summary cards

---

# 6. Seed data plan

Seed data is mandatory.

## Required content seed

Create around 12–20 sample posts distributed across categories:

- SEO
- Blogging
- AI Tools
- Content Marketing
- Python
- Web Development

## Content expectations

Posts should be long enough for:

- readability scoring
- keyword extraction
- similarity comparisons
- recommendation variety

## Optional interaction seed

If useful, add sample interactions so the dashboard looks populated even before manual testing.

---

# 7. Execution waves

## Wave 1 — Foundation

### Goal

Get the app skeleton running.

### Deliverables

- Flask app setup
- config
- database models
- migrations or init script
- base layout
- homepage
- post detail page
- seed script
- seeded posts visible in UI

### Definition of done

- app starts
- DB initializes
- homepage and post page render
- sample content loads

---

## Wave 2 — Author features + SEO

### Goal

Enable post authoring and analysis.

### Deliverables

- create/edit post form
- SEO service
- SEO score and suggestions display
- optional stored SEO report

### Definition of done

- a post can be created or edited
- analysis runs successfully
- analysis result is visible in UI

---

## Wave 3 — Similarity / internal linking

### Goal

Enable related-post and internal-link suggestions.

### Deliverables

- TF-IDF similarity service
- top related posts computation
- integration into author analysis and/or post detail view

### Definition of done

- current post shows 3–5 relevant internal suggestions
- obviously unrelated posts are not dominating results

---

## Wave 4 — Personalization

### Goal

Make reader recommendations adapt.

### Deliverables

- session token creation/retrieval
- interaction logging
- interest profile logic
- ranked recommendation function
- recommendation UI on post page

### Definition of done

- reading behavior changes recommendation output
- already viewed posts are deprioritized

---

## Wave 5 — Analytics + final polish

### Goal

Make the platform demo-ready.

### Deliverables

- dashboard route
- analytics service
- charts/cards
- seed improvements
- UI cleanup
- README with setup/demo flow

### Definition of done

- dashboard renders
- metrics look sensible
- demo flow can be run start-to-finish

---

# 8. Parallelization plan

## Agent A — Foundation

Scope:

- app structure
- config
- DB models
- base templates
- seed setup
- core routes skeleton

## Agent B — SEO

Scope:

- SEO analysis service
- keyword extraction
- readability scoring
- scoring logic
- suggestions formatting

## Agent C — Similarity

Scope:

- TF-IDF vectorization
- related-post engine
- internal link suggestion formatting

## Agent D — Personalization + Analytics

Scope:

- sessions/interactions
- ranking logic
- dashboard aggregation
- charts data

## Agent E — Integration / UX polish

Scope:

- template cohesion
- feature wiring
- bugfixes across subsystem boundaries
- README and demo support

---

# 9. Merge order

Recommended merge order:

1. Foundation
2. SEO
3. Similarity
4. Personalization
5. Analytics / polish

Reason:

- everything depends on the foundation
- SEO and similarity depend on post/content structure
- personalization depends on view/interactions existing
- analytics depends on collected data
- polish should happen last

---

# 10. Merge safety rules

- Keep branches small and scoped
- Avoid unnecessary renames
- Do not reformat entire files
- Touch shared files only when required
- Rebase or merge often enough to avoid drift
- Validate app startup before merging
- Prefer incremental integration over giant final merges

---

# 11. Testing checklist

## App-level

- app boots
- no template crashes
- DB initializes cleanly
- seed data runs

## Content

- post listing works
- post detail works
- create/edit works

## SEO

- SEO analysis returns data
- score and suggestions render
- weird empty inputs are handled reasonably

## Similarity

- related posts appear
- self-post is excluded
- results are plausible

## Personalization

- session is created
- interaction is logged
- recommendations change based on reading flow

## Dashboard

- metrics populate
- charts render
- no crash on empty-ish states

---

# 12. Demo script

## Demo A: Author flow

1. Open author page
2. Create/edit a post
3. Run SEO analysis
4. Show SEO score
5. Show suggestions
6. Show internal link suggestions

## Demo B: Reader flow

1. Browse homepage
2. Read posts in a single category
3. Open another post
4. Show personalized recommendations responding to behavior

## Demo C: Analytics flow

1. Open dashboard
2. Show top posts
3. Show category trends
4. Show dwell time / recommendation clicks
5. Show content quality snapshots

---

# 13. Success criteria

The MVP is successful if:

- it runs locally without drama
- it clearly demonstrates author-side intelligence
- it clearly demonstrates reader-side personalization
- it clearly demonstrates platform analytics
- the code structure is understandable
- the demo story is clean and believable

---

# 14. Philosophy for implementation

Under this deadline, the right tradeoff is:

- simple over flashy
- explainable over opaque
- integrated over fragmented
- demoable over theoretically perfect

This project should feel like a real product, not a pile of disconnected features.

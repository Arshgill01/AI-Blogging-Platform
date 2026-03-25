---
name: flask-foundation
description: Use this skill when setting up or extending the Flask app skeleton, database models, routing structure, templates, configuration, and seed flow for the AI-Powered Blogging Platform.
---

# Flask Foundation

## Purpose

This skill establishes and extends the foundational application structure for the AI-Powered Blogging Platform.

Use this skill when the task involves:

- Flask app setup
- project structure
- configuration
- SQLAlchemy models
- route skeletons
- template base
- seed scripts
- app boot stability

This project is a self-contained product:

- no internet scraping
- no external blogging engines
- no external recommendation APIs

All logic must operate on internal platform content and in-platform behavior.

---

## Primary goals

Build a clean, modular Flask application that supports:

- author pages
- reader pages
- analytics/dashboard pages
- database-backed posts
- sessions/interactions
- future SEO and recommendation services

The output must be stable, understandable, and easy for other agents to extend.

---

## Preferred stack

- Flask
- SQLite
- SQLAlchemy
- Jinja templates
- Bootstrap

Keep infrastructure lightweight.
Do not introduce unnecessary frameworks or deployment complexity.

---

## Architectural expectations

### App shape

Prefer a modular layout such as:

```text
app/
  __init__.py
  models.py
  routes/
    main.py
    posts.py
    analytics.py
  services/
  templates/
  static/
  seed.py
run.py
requirements.txt
```

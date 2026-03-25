---
name: analytics-dashboard
description: Use this skill when implementing dashboard metrics, analytics aggregation, and visual summaries of content performance and reader engagement.
---

# Analytics Dashboard

## Purpose

This skill implements the admin/observer side of the platform: turning stored interactions and content metadata into useful dashboard metrics.

Use this skill when the task involves:

- analytics aggregation
- dashboard cards
- charts
- post performance summaries
- category engagement summaries
- recommendation click metrics

---

## Product role

The dashboard should help demonstrate that the platform is:

- tracking engagement
- adapting to reader behavior
- evaluating content quality

It is a major part of the product story and demo.

---

## Design philosophy

Prefer:

- clear summary metrics
- simple aggregation queries
- understandable charts
- graceful handling of sparse data

This dashboard does not need to be enterprise analytics.
It needs to be coherent and demoable.

---

## Core metrics to support

At minimum show:

- total posts
- total interactions
- total sessions if available
- top viewed posts
- category popularity
- average dwell time
- recommendation click counts
- SEO score snapshots by post if available

Optional:

- recent activity summaries
- average readability / content score
- per-category engagement cards

---

## Visualization guidance

Use Chart.js or simple server-rendered summaries.

Good charts:

- bar chart for top posts
- pie/donut or bar chart for category popularity
- line or bar chart for engagement counts if time permits

Do not overbuild the visualization layer.

---

## Data sources

This skill may aggregate from:

- posts
- visitor sessions
- interactions
- SEO reports

Keep the aggregation logic modular and testable.

---

## Good implementation choices

Prefer:

- analytics service functions returning clean dictionaries/lists
- routes that prepare dashboard-ready data
- templates that render clean cards and charts
- fallback states for empty data

For example:

- "No interaction data yet" should render cleanly, not crash

---

## Integration targets

The dashboard should work with:

- content seed data
- manual browsing interactions
- stored SEO analysis results

If seeded interactions are added, the dashboard should display them cleanly.

---

## Constraints

Do not:

- introduce a heavy BI layer
- depend on external analytics tools
- create fragile chart plumbing
- couple aggregation tightly to templates

---

## Working style

When using this skill:

1. Build the service layer first.
2. Keep metric names explicit.
3. Ensure the UI remains readable with small data volumes.
4. Prefer 3–6 strong metrics over 20 weak ones.

---

## Definition of done

This skill is successful when:

- the dashboard route renders
- metrics are populated from app data
- charts/cards are readable
- the dashboard strengthens the demo story

---

## Coordination notes

This skill depends on:

- interaction logging
- session data
- post data
- optional SEO report data

It should focus on aggregation and presentation, not event collection itself.

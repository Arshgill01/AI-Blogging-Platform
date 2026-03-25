---
name: integration-demo-polish
description: Use this skill when integrating subsystems, tightening the UI/UX, fixing cross-module issues, improving demo readiness, and preparing the final project flow.
---

# Integration Demo Polish

## Purpose

This skill is for the final integration phase:
making the app feel like one coherent product instead of separate subsystems.

Use this skill when the task involves:

- feature wiring
- cross-module bugfixes
- template cohesion
- demo flow cleanup
- seed quality improvements
- README/demo instructions

---

## Product role

By the time this skill is used, the project should already have:

- app foundation
- SEO analysis
- similarity logic
- personalization logic
- dashboard logic

This skill makes all of it presentable, stable, and easy to demonstrate.

---

## Main goals

- make routes and templates feel consistent
- reduce friction in the main user flows
- ensure author, reader, and dashboard flows work end-to-end
- improve seed/demo quality
- document how to run and demonstrate the system

---

## Demo flows to protect

### Author flow

1. Create or edit a post
2. Run SEO analysis
3. View SEO score and suggestions
4. View internal link suggestions

### Reader flow

1. Browse homepage
2. Open posts
3. Generate session behavior
4. Observe recommended reads adapting

### Dashboard flow

1. Open dashboard
2. Show top posts
3. Show category interest
4. Show engagement and SEO summaries

These flows matter more than minor implementation elegance at this stage.

---

## Polish priorities

### 1. UI cohesion

- consistent navigation
- consistent cards/forms/buttons
- readable result sections
- no broken spacing or jarring layouts

### 2. Stability

- no crashing routes
- graceful fallback states
- no obviously broken template assumptions

### 3. Demo readiness

- strong seed content
- metrics visible quickly
- recommendations and related posts visibly working
- clear setup instructions

### 4. README quality

The README should cover:

- project overview
- features
- tech stack
- setup steps
- how to seed data
- how to run locally
- suggested demo walkthrough

---

## Good implementation choices

Prefer:

- small integration fixes
- targeted template cleanup
- explicit empty-state handling
- route-to-route consistency
- concise documentation

Avoid:

- late-stage deep refactors
- redesigning architecture during polish
- changing subsystem ownership unless necessary to unbreak integration

---

## Testing expectations

Before calling integration done, verify:

- app boots cleanly
- seed works
- main nav works
- create/edit flow works
- SEO output renders
- related posts render
- recommendations render
- dashboard renders
- no obvious dead links or broken templates

---

## Working style

When using this skill:

1. Think like the final demo reviewer.
2. Prioritize visible coherence.
3. Fix the highest-leverage issues first.
4. Avoid destabilizing finished subsystems.

---

## Definition of done

This skill is successful when:

- the product feels unified
- the key flows are smooth
- the app is demo-ready
- the README is usable
- a reviewer can understand what the project does quickly

---

## Coordination notes

This skill touches many modules, so use restraint.
Prefer minimal, high-value changes that improve the whole experience.

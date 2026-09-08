---
name: resume-refiner
description: Refines and polishes a candidate's master resume in general (upgrading action verbs, quantifying results with Google XYZ formula, removing passive voice) while strictly preserving their custom layout, section order, headers, and zero-hallucination truth guardrails.
---

# Resume Refiner Skill

This skill provides comprehensive capabilities to review, upgrade, and polish a candidate's master resume **in general** (independent of individual job applications), while honoring two ironclad rules:
1. **Strict Format Preservation**: Never reformat the user's resume into an alien layout. Every header, section sequence, contact line, and bullet style (`-`, `*`, `•`) must remain intact.
2. **The Truth Layer (Zero Hallucination)**: Never invent fake metrics, tools, or frameworks. Any technology mentioned must exist in the candidate's verified skills whitelist.

## Core Optimization Principles

### 1. The Google XYZ Impact Formula
Rewrite passive experience bullets to follow:
> **Accomplished [X] as measured by [Y], by doing [Z]**

- *Weak*: "Worked on backend APIs for our payment platform."
- *Strong*: "Engineered high-throughput REST APIs handling 50k+ daily transactions in FastAPI, reducing checkout latency by 35% with Redis caching."

### 2. Action Verb Hierarchy
Replace weak verbs with definitive power verbs:
- "Helped with / Assisted" -> "Collaborated on architecting"
- "Responsible for" -> "Spearheaded / Orchestrated"
- "Looked into bugs" -> "Diagnosed and resolved critical race conditions"
- "Made code changes" -> "Implemented scalable microservices"

### 3. Workflow
1. Read the candidate's raw master resume text.
2. Validate skills against `master_profile.skills` or `allowed_skills`.
3. Apply surgical bullet improvements.
4. Verify every upgraded bullet against `validate_tech_stack`.
5. Return the polished resume with an audit log of specific bullet improvements and rationales.

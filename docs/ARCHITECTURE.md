# Architecture Notes

This document expands on the agent pipeline summarised in the README.

## Data flow

1. **AssessmentRequest** (topic + syllabus) enters the **Orchestrator**.
2. **Syllabus Parser** turns free-text syllabus lines into structured, testable
   skills, plus the implied ROS2 APIs, config elements and components.
3. **Source Research** attaches reference material (offline-curated by default).
4. **Coverage Matrix** is initialised from the parsed skills.
5. **Question Generator** selects templates (offline) or prompts the model (LLM)
   to produce engineering-ticket questions, filling coverage gaps first and
   cycling industrial domains so successive questions stay distinct.
6. A validation fan-out runs over the candidate questions and **mutates them in
   place**: Boilerplate, Difficulty, Originality, Scope, Realism, Auto-Grading.
7. **Confidence Scoring** computes a weighted score and sets each question's
   APPROVED/REJECTED status.
8. The hiring agents (**Role**, **Hiring Signal**, **Market**, **Portfolio**)
   annotate the questions and compute portfolio coverage.
9. **Evaluation** scores the batch across nine criteria.
10. The **AssessmentPackage** is assembled and handed to the **Supervisor**,
    which performs independent final validation and emits a verdict.

## Agent contract

Every agent extends `BaseAgent` and returns an `AgentResult` envelope. Structured
payloads travel as plain dicts in `AgentResult.payload`; the Orchestrator
reconstructs Pydantic models from them. Validation agents additionally mutate the
`Question` objects passed to them so downstream agents and the package see the
annotations.

## Why offline-first?

A deterministic template engine guarantees the pipeline is runnable, testable and
reproducible with no credentials and no network — which is exactly what CI and
graders need. The LLM path reuses the same schemas, selection logic and quality
gates, so enabling it does not bypass any validation.

## Persistence

- `logs/runs.db` — run + per-stage event log (audit trail).
- `memory/memory.db` — analysis cache and a record of emitted question stems,
  used to keep future cohorts original.
- `vectorstore/index.json` — bag-of-words vectors backing cosine-similarity
  originality checks.

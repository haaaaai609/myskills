---
name: feature-evolution
description: Use this skill when the user wants to modify, extend, or add functionality in an existing software system. It updates existing project design and development documentation in place, then implements the feature according to the revised plan. Do not use for brand-new projects or bug-only diagnosis.
---

# Feature Evolution

## Purpose

Evolve an existing system without losing design consistency. Inspect the current implementation and documentation first, update the relevant docs in place, then implement the requested feature from the revised plan.

Match the user's language for questions, docs, and summaries.

## Trigger Boundary

Use this skill for:

- New features, feature modifications, workflow changes, UI changes, API changes, behavior changes, or integrations in an existing project.
- Requests such as "add a feature", "modify this system", "extend the current app", "change the existing workflow", or "develop based on the existing project".
- Repositories that already contain meaningful application code, docs, tests, or deployment config.

Do not use this skill for:

- Greenfield projects or first implementations in an empty repo; use the new-project workflow instead.
- Error reports, failing tests, exceptions, broken deployments, or debugging tasks where the primary request is diagnosis; use the bug diagnosis workflow first.
- Pure code review unless the user asks to implement a feature change after the review.

## Workflow

1. Ground in the existing system.
   - Inspect relevant code, routes, schemas, tests, docs, package manifests, config, and git state.
   - Identify the current architecture, conventions, doc locations, and feature ownership boundaries.
   - Prefer repository conventions over new structures.

2. Clarify only unresolved product or technical decisions.
   - Ask questions only when the answer materially changes design, data contracts, user workflows, compatibility, or rollout.
   - Do not ask for facts that can be discovered from files.
   - State assumptions when the risk is low and proceed.

3. Update documentation in place.
   - Find the existing design docs and development docs that describe the affected area.
   - Insert or revise content in the appropriate sections; do not blindly append a new block to the end.
   - Keep the old and new behavior clear, including compatibility notes if behavior changes.
   - If no relevant docs exist, create them under `docs/spec/` for design and `docs/plan/` for implementation planning.
   - Keep design docs and development docs consistent with each other.

4. Update the development plan.
   - Add or revise the implementation tasks in the existing plan document when one exists.
   - Include affected modules, interface/API changes, data/schema changes, tests, verification commands, rollout notes, and risks.
   - Keep the plan specific enough that implementation decisions are already settled.

5. Implement according to the revised plan.
   - Keep changes scoped to the feature and the affected docs.
   - Preserve existing public behavior unless the docs and user intent require a change.
   - Follow established local patterns for architecture, naming, styling, tests, and error handling.
   - Pause for confirmation before high-risk actions.

6. Verify and report.
   - Run relevant tests, builds, type checks, linters, or smoke checks.
   - For frontend changes, verify responsive behavior and start the dev server when appropriate.
   - Summarize doc updates, code changes, verification results, and remaining risks.

## Documentation Rules

- Update existing docs in place whenever possible.
- Insert changes into the correct section based on the feature's impact.
- Do not simply append "new feature" sections at the bottom unless the document structure explicitly uses append-only change records.
- If the repository has no suitable docs, create:
  - `docs/spec/` for system or feature design.
  - `docs/plan/` for implementation plans.
- Keep docs synchronized with implemented behavior.

## Confirmation Rules

Proceed with ordinary feature implementation after docs and plan are updated. Pause for user confirmation before:

- Architecture rewrites or new major subsystems.
- Database migrations, schema migrations, or irreversible data changes.
- Dependency installation, dependency upgrades, or framework changes.
- Destructive file operations or broad rewrites.
- Deployment, infrastructure, secrets, permission, or external-service changes.
- Any change with unclear compatibility impact.

Respect all higher-priority Codex instructions, sandbox restrictions, and collaboration-mode rules.

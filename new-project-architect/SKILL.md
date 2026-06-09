---
name: new-project-architect
description: Use this skill when the user wants to start a brand-new software project, scaffold a new application from zero, or turn an initial product idea into requirements, design docs, a development plan, and implementation. Do not use for feature changes in an existing system or bug/error diagnosis.
---

# New Project Architect

## Purpose

Guide a new project from idea to implementation. Clarify the product intent first, write complete project design documentation under `docs/spec/`, write an implementation plan under `docs/plan/`, then build from that plan.

Match the user's language for questions, docs, and summaries.

## Trigger Boundary

Use this skill for:

- New projects, greenfield applications, prototypes, services, tools, websites, games, or libraries.
- Requests such as "start a new project", "build a new app", "create a system from scratch", "scaffold a new service", or "turn this idea into a product".
- Empty or mostly empty repositories where the user is asking for the first real product implementation.

Do not use this skill for:

- Adding or modifying features in an existing system; use the existing-feature workflow instead.
- Error reports, failing tests, exceptions, broken deployments, or debugging tasks; use the bug diagnosis workflow instead.
- Pure explanation, review, or planning requests where the user explicitly does not want implementation.

## Workflow

1. Ground in the workspace before asking questions.
   - Inspect the repository structure, package manifests, README/docs, existing config, and git state when available.
   - Identify whether the workspace is empty, partially scaffolded, or already an existing application.
   - If the repo is clearly an existing system and the request is feature work, stop using this skill and switch to the existing-feature workflow.

2. Run Socratic requirement clarification.
   - Ask focused questions that materially change the product, architecture, or implementation plan.
   - Prefer short batches of 1-3 questions.
   - Clarify at least: target users, core workflows, success criteria, data model, integrations, auth/security needs, deployment target, constraints, non-goals, and acceptance tests.
   - Do not ask questions that can be answered from local files or commands.
   - If the user gives enough detail, state the remaining assumptions and proceed.

3. Write the system design.
   - Create `docs/spec/` if it does not exist.
   - Write a complete design document in `docs/spec/` before implementation.
   - Include: goals, non-goals, user workflows, architecture, key modules, data model, API/interface contracts, UI/UX behavior when relevant, security/privacy considerations, operational concerns, and acceptance criteria.
   - Use a clear filename based on the project or feature, such as `docs/spec/system-design.md`, unless the repo already has a naming convention.

4. Write the development plan.
   - Create `docs/plan/` if it does not exist.
   - Write a detailed implementation plan in `docs/plan/` before implementation.
   - Include: phased tasks, file/module areas, public interfaces, data/schema changes, test strategy, verification commands, rollout steps, and known risks.
   - Use a clear filename such as `docs/plan/development-plan.md`, unless the repo already has a naming convention.

5. Implement from the plan.
   - Follow the plan in order and keep edits scoped to the new project.
   - Use the repository's chosen stack and conventions once established.
   - If the plan requires high-risk actions, ask for explicit confirmation before performing them.
   - High-risk actions include destructive file operations, data migrations, architecture pivots, external dependency installation, credential handling, deployment changes, or broad rewrites.

6. Verify and report.
   - Run relevant tests, builds, type checks, linters, or smoke checks.
   - If a frontend app needs a dev server, start it and provide the URL.
   - Summarize created docs, implemented behavior, verification results, and any remaining risks.

## Documentation Rules

- Project design belongs in `docs/spec/`.
- Development plans belong in `docs/plan/`.
- Create missing directories.
- Prefer updating an existing relevant document only when the repository already has a clear convention for project design or plans.
- Keep docs actionable enough that another engineer can implement from them.

## Confirmation Rules

Proceed after clarification, design, and planning are complete. Pause for user confirmation before any high-risk action:

- Installing or upgrading dependencies.
- Running migrations or commands that change external systems.
- Deleting or replacing substantial existing files.
- Changing deployment, infrastructure, secrets, or permissions.
- Making a major architecture choice that was not already agreed during clarification.

Respect all higher-priority Codex instructions, sandbox restrictions, and collaboration-mode rules.

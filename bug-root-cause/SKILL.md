---
name: bug-root-cause
description: Use this skill when the user reports an error, exception, failing command, failed test, broken behavior, crash, log output, or production/debugging issue. It requires diagnosis and root-cause explanation before any code modification, then asks the user whether to apply a fix.
---

# Bug Root Cause

## Purpose

Diagnose system failures before changing code. Gather evidence, identify the likely root cause, explain it to the user, and ask whether to apply a fix before making any code edits.

Match the user's language for questions, analysis, and summaries.

## Trigger Boundary

Use this skill for:

- Error messages, stack traces, failed commands, failing tests, crashes, broken behavior, regressions, log analysis, deployment failures, and production incidents.
- Requests such as "报错了", "debug this", "why is this failing", "fix this error", "tests fail", "service cannot start", or "analyze these logs".

Do not use this skill for:

- Planned feature work without an observed failure.
- New project creation.
- Refactors or enhancements where there is no bug or error to diagnose.

## Non-Negotiable Rule

Do not modify code, configuration, migrations, docs, or tracked files before presenting the root-cause analysis and asking the user whether to apply the fix.

Allowed before approval:

- Read files and logs.
- Search the repository.
- Inspect configuration.
- Run non-mutating diagnostics.
- Run tests or commands needed to reproduce the issue, as long as they do not intentionally rewrite tracked files.

Not allowed before approval:

- Applying patches.
- Editing source, config, docs, lockfiles, or migrations.
- Running formatters or code generators that rewrite tracked files.
- Restarting, deleting, migrating, or changing external state unless the user explicitly requested that diagnostic action and permissions allow it.

## Workflow

1. Gather evidence.
   - Read the user's error, logs, command output, and reproduction notes.
   - Inspect relevant code, config, dependencies, tests, and recent changes.
   - Reproduce the issue when feasible with scoped commands.
   - Avoid destructive or state-changing commands unless explicitly approved.

2. Analyze root cause.
   - Identify the failing component and the causal chain.
   - Separate direct evidence from inference.
   - Consider recent changes, environment mismatch, dependency versions, data shape, permissions, networking, and config.
   - If there are multiple plausible causes, rank them by likelihood and name what evidence would distinguish them.

3. Report before fixing.
   - Explain the likely root cause in user-facing language.
   - Include key evidence: files, lines, logs, commands, or observed behavior.
   - State affected components and confidence level.
   - Describe the proposed fix and verification plan.
   - Ask the user whether to apply the fix.

4. Fix only after approval.
   - Keep edits scoped to the diagnosed cause.
   - Avoid unrelated refactors.
   - Add or update regression tests when practical.
   - Run the verification plan.

5. Final report.
   - Summarize root cause, files changed, tests run, and residual risk.
   - If no fix was applied, summarize the diagnosis and next diagnostic step.

## Approval Prompt

Before editing, ask a direct question such as:

"I found the likely root cause: [brief cause]. The fix is [brief fix]. Do you want me to apply it?"

If the user has already explicitly approved fixing after seeing the diagnosis, proceed.

Respect all higher-priority Codex instructions, sandbox restrictions, and collaboration-mode rules.

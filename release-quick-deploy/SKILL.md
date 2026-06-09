---
name: release-quick-deploy
description: Create fast offline deployment release packages for projects that need to be copied to another server and deployed with a small set of shell commands. Use when Codex is asked to analyze an existing Docker Compose or multi-service project and generate a release/ directory, offline image/package layout, .env examples, deploy/maintenance scripts, README deployment instructions, or a reusable manifest-driven release skeleton.
---

# Release Quick Deploy

## Overview

Use this skill to turn a repo into a customer-site release package that can be copied to a server and deployed quickly with `bash scripts/release.sh init`, `preflight`, `start`, and project-specific post-start commands.

The bundled I3D release pattern reference captures the reusable model: offline Docker images, stable runtime images, hot-swappable service packages, runtime assets, SQL, frontend static files, persistent data directories, and scripts for deployment and maintenance. Do not assume any absolute local path exists on the target machine; rely on this skill's bundled references and the project being analyzed.

## Workflow

1. Inspect the project before writing files. Read compose files, Dockerfiles, service startup scripts, env examples, package/build scripts, frontend output paths, SQL init files, runtime/model/native-library assets, and any existing deployment docs.
2. Classify deliverables into clear release boundaries:
   - `images/infra`: low-change middleware or base runtime images.
   - `images/services`: application service images that change with business releases.
   - `projects/<service>/code`: hot-swappable app packages mounted into stable runtime images.
   - `frontend`: web static assets, nginx config, and optional desktop installers.
   - `runtime`: models, SDKs, native libraries, licenses, or hardware runtime assets kept outside images.
   - `sql`: database initialization scripts and schema snapshots.
   - `infra`: persistent data, service workspaces, and logs created by `init`; do not put SDKs, source code, or delivery artifacts here.
   - `bin`: host binaries that should run outside Docker, with a separate manager script if needed.
3. Decide whether the project can use the manifest generator. Use `scripts/generate_release_package.py` when the service topology can be described as JSON. Hand-edit or extend the generated files when the project needs unusual compose features, custom migrations, hardware devices, or host daemons.
4. Generate or edit the release package. Prefer an explicit `release-manifest.json` in the project or a temporary manifest beside the target release directory.
5. Validate from the release root:
   - `bash scripts/release.sh init`
   - `bash scripts/release.sh preflight --skip-images --skip-pkg` during skeleton creation
   - `docker compose -f docker-compose.yml -f docker-compose.services.yml config` when Docker Compose is available
   - Project-specific package, image, migration, health, and reset checks when artifacts exist

## Generation

Create a manifest from the project analysis, then run:

```bash
python3 /path/to/release-quick-deploy/scripts/generate_release_package.py \
  --manifest /path/to/release-manifest.json \
  --output /path/to/project/release \
  --force
```

Use `--force` only for a generated release directory you are ready to overwrite. The script writes a generic deployable skeleton: `README.md`, `.env.example`, compose files, `scripts/release.sh`, placeholder directories, SQL/frontend placeholders when requested, and `release-manifest.json`.

For the manifest shape and examples, read `references/manifest-schema.md`.

## I3D Pattern

Read `references/i3d-release-pattern.md` when adapting an existing service layout or explaining why the release directory is structured this way. It maps the I3D release directories to their operational responsibilities and lists the reusable script commands.

## Design Rules

Keep release packages boring and explicit:

- Put all site-specific knobs in `.env.example`; compose files should reference env vars instead of hard-coding passwords, ports, public hosts, image tags, or hardware choices.
- Use project-specific container prefixes, compose project names, networks, and host port ranges to avoid collisions with development environments.
- Separate infra compose from business-service compose so middleware baselines can stay stable while service packages/images change.
- Keep destructive operations opt-in. Require `reset --yes`, protect broad directories, and never delete deliverable artifacts such as `.env`, `images`, `projects`, `runtime`, `frontend`, `bin`, or local Docker images during reset.
- Make preflight fail early for missing env, occupied ports, missing compose files, missing packages, missing frontend files, missing SQL files, and missing images unless explicitly skipped.
- Document first deployment and daily maintenance in the release README, including update package, save images, restart, logs, health, stop, down, and reset flows.
- For GPU/NPU or other hardware variants, keep the same release directory contract and add variant env examples or compose override files instead of forking the whole release layout.

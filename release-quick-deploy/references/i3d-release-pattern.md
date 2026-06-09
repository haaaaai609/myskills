# I3D Release Pattern

Use this reference when adapting the bundled I3D-style release package model to another project. The model is documented here so the agent does not need access to any original local project path.

## Directory Responsibilities

`release/` is the customer-site deployment root. It excludes internal tests, source build templates, historical compatibility files, and developer-only artifacts.

- `.env.example`, `.env.npu.example`: site-editable deployment contracts. They define image tags, host ports, credentials, public endpoints, workers, runtime paths, tenant IDs, and hardware settings.
- `docker-compose.yml`: middleware/infra layer. I3D uses PostgreSQL+pgvector, Redis, RabbitMQ, MinIO, XXL-Job MySQL, and XXL-Job Admin.
- `docker-compose.services.yml`: business services and frontend. It references the infra network and env vars.
- `docker-compose.services.npu.yml`: hardware variant for Ascend/NPU while preserving the same release directory contract.
- `scripts/release.sh`: Docker deployment and maintenance entrypoint.
- `scripts/aether-monitor.sh`: optional host-binary/systemd manager for Aether resource monitoring. Use this pattern only when a process should run on the host instead of in Docker.
- `frontend/`: nginx config, static web build, and optional desktop installers.
- `images/infra/`: offline tar images for low-change middleware and frontend nginx.
- `images/services/`: offline tar images for business service runtime images.
- `projects/<service>/code/<service>.pkg`: hot-swappable service packages mounted into containers. Business code changes can replace pkg files and restart services without rebuilding runtime images.
- `runtime/`: large or hardware-specific runtime assets such as SDKs, native libraries, model files, and licenses.
- `sql/`: database initialization scripts and schema snapshots. I3D uses container-entrypoint SQL for pgvector and XXL-Job, while business schema setup is driven by Django migrations.
- `infra/`: persistent middleware data plus service workspaces/logs. `init` creates it; `reset --yes` cleans only runtime data, not deliverables.
- `bin/`: host executables such as Aether.
- `config/`: supplemental container runtime config, such as GLVND/EGL vendor files for GPU rendering.
- `shared/`: optional cross-service exchange area when a project needs one.

## Script Responsibilities

`scripts/release.sh` provides one main operational surface:

- `init`: create release directories and copy `.env.example` to `.env` if missing.
- `preflight`: validate env values, port conflicts, required files, packages, images, and compose config.
- `ports`: check host port conflicts while ignoring containers from the current compose project.
- `images load`: import offline image tar files.
- `images save`, `images save-infra`, `images save-all`: export service, infra, or full image sets.
- `start`: create dirs, sync missing/stale images from tar, run preflight, start infra, start services, and run post-start hooks.
- `stop`: stop containers without deleting data.
- `down`: remove containers and network without deleting data.
- `reset --yes`: remove containers/network and clean runtime data directories while preserving deliverables and local Docker images.
- `status`: show package paths and compose status.
- `restart <service|all>`: recreate logical services; one logical service can map to multiple compose roles.
- `update-pkg <service> <pkg> [--restart]`: atomically replace a pkg, write sha256, and optionally restart related roles.
- `migrate`: run project-specific database migrations inside a service container.
- `health <service|all>`: check host-reachable HTTP health endpoints.
- `logs <service|all> [--tail N]`: follow logs for logical services or all roles.

`scripts/aether-monitor.sh` is separate because Aether is a host binary managed by systemd:

- `init`: verify binaries and runtime directory.
- `install`, `uninstall`: write/remove a systemd unit.
- `start`, `stop`, `restart`, `status`, `logs`: manage systemd.
- `health`: call the host binary health command.
- `run`: export runtime env and exec the binary.

## Reusable Architecture Decisions

- Keep runtime images stable and mount service packages at runtime. This reduces image rebuilds when only business code changes.
- Split image tar directories into infra and services. Site operators usually load infra once and refresh services more often.
- Make image loading idempotent. I3D compares the local image ID with the tar manifest image ID and skips imports when already current.
- Keep model/native/runtime assets outside images when they are large, licensed, hardware-specific, or frequently replaced.
- Map host paths explicitly. I3D maps host model data into containers for server-side scanning and warns not to scan broad roots such as `/data`.
- Use release-specific port ranges and Docker names to avoid local-dev conflicts.
- Keep hardware variants as env/compose overrides. I3D's GPU variant uses NVIDIA device reservations and GLVND config; the NPU variant mounts Ascend drivers/devices and uses `.om` model paths.
- Protect reset. I3D refuses to clean broad paths such as `/`, `/data`, `/home`, `/root`, `/tmp`, `/usr`, `/var`, `/var/lib`, or the release root itself.

## Adaptation Checklist

For another project, identify:

- Infra services and whether each needs persistent data, init SQL, health checks, and host ports.
- Business services, internal ports, health URLs, dependencies, startup commands, app package names, log directories, and worker roles.
- Frontend static output, nginx config, and public port.
- Runtime assets that should be copied as files instead of baked into images.
- SQL initialization and migration commands.
- Host binaries or system services that should be managed outside Docker.
- Hardware variants and device mounts.
- Post-start hooks such as bucket policy setup, migration, search index sync, tenant initialization, or scheduler registration.

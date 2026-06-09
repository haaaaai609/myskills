#!/usr/bin/env python3
"""Generate a manifest-driven offline release deployment skeleton."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import stat
import sys
from pathlib import Path
from typing import Any


COMMON_PORTS = {
    "postgres": 5432,
    "redis": 6379,
    "rabbitmq": 5672,
    "minio": 9000,
    "mysql": 3306,
}


def fail(message: str) -> None:
    print(f"[generate-release][FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON manifest: {path}: {exc}")
    if not isinstance(data, dict):
        fail("manifest root must be an object")
    if not isinstance(data.get("project"), dict):
        fail("manifest must contain object field: project")
    return data


def normalize_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip())
    return value.strip("-").lower()


def env_key(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return value or "VALUE"


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def ensure_clean_output(output: Path, force: bool) -> None:
    if output.exists():
        if not force:
            fail(f"output already exists, pass --force to overwrite: {output}")
        if output.resolve() in {Path("/").resolve(), Path("/data").resolve(), Path("/tmp").resolve()}:
            fail(f"refusing to remove broad output path: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)


def write_text(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return '""'
    text = str(value)
    if text == "":
        return '""'
    if text.startswith("*"):
        return text
    if text.startswith("${") or text.startswith("./") or text.startswith("/") or text.startswith("http://") or text.startswith("https://"):
        return text
    if re.match(r"^[A-Za-z0-9_.:/@%+,-]+$", text):
        return text
    return json.dumps(text, ensure_ascii=False)


def yaml_dump(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(yaml_dump(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {yaml_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(yaml_dump(item, indent + 2))
            else:
                lines.append(f"{pad}- {yaml_scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{yaml_scalar(value)}"


def env_ref(var_name: str, default: Any | None = None, required: bool = True) -> str:
    if default is not None:
        return "${" + var_name + ":-" + str(default) + "}"
    if required:
        return "${" + var_name + ":?set " + var_name + " in .env}"
    return "${" + var_name + ":-}"


def collect_services(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    infra = [dict(item) for item in as_list(manifest.get("infra")) if isinstance(item, dict)]
    services = [dict(item) for item in as_list(manifest.get("services")) if isinstance(item, dict)]
    frontend = manifest.get("frontend")
    if isinstance(frontend, dict) and frontend.get("enabled", True):
        frontend_data: dict[str, Any] | None = dict(frontend)
    else:
        frontend_data = None
    return infra, services, frontend_data


def image_var(service: dict[str, Any]) -> str:
    return str(service.get("image_var") or f"{env_key(str(service['name']))}_IMAGE")


def host_port_var(service: dict[str, Any]) -> str:
    return str(service.get("host_port_var") or f"{env_key(str(service['name']))}_HOST_PORT")


def container_port(service: dict[str, Any]) -> int:
    if "container_port" in service:
        return int(service["container_port"])
    service_type = str(service.get("type", "")).lower()
    return COMMON_PORTS.get(service_type, int(service.get("port", 8080)))


def service_pkg_name(service: dict[str, Any]) -> str:
    return str(service.get("pkg_name") or f"{service['name']}.pkg")


def default_health_path(service: dict[str, Any]) -> str:
    return str(service.get("health_path") or "/health/")


def env_example(manifest: dict[str, Any]) -> str:
    project = manifest["project"]
    infra, services, frontend = collect_services(manifest)
    lines: list[str] = [
        f"# {project.get('display_name') or project['name']} customer-site deployment config",
        "",
        f"COMPOSE_PROJECT_NAME={project.get('compose_project_name') or normalize_name(project['name']) + '-customer-release'}",
        f"CONTAINER_PREFIX={project.get('container_prefix') or normalize_name(project['name']) + '-release'}",
        f"RELEASE_NETWORK={project.get('network') or normalize_name(project['name']).replace('-', '_') + '_customer_release'}",
        f"TZ={project.get('timezone') or 'Asia/Shanghai'}",
        "",
        "# Offline image tags",
    ]
    for item in infra + services:
        lines.append(f"{image_var(item)}={item.get('image') or item['name'] + ':latest'}")
    if frontend:
        lines.append(f"{frontend.get('image_var') or 'FRONTEND_IMAGE'}={frontend.get('image') or 'nginx:alpine'}")

    lines.extend(["", "# Host ports"])
    for item in infra + services:
        if item.get("host_port") is not None:
            lines.append(f"{host_port_var(item)}={item['host_port']}")
    if frontend:
        lines.append(f"{frontend.get('host_port_var') or 'FRONTEND_HOST_PORT'}={frontend.get('host_port', 48100)}")

    lines.extend(["", "# Infra defaults"])
    for item in infra:
        for key, value in dict(item.get("env") or {}).items():
            lines.append(f"{key}={value}")

    lines.extend(["", "# Service defaults"])
    for item in services:
        for key, value in dict(item.get("env_defaults") or {}).items():
            lines.append(f"{key}={value}")

    for key, value in dict(manifest.get("env_defaults") or {}).items():
        lines.append(f"{key}={value}")

    return "\n".join(lines).rstrip() + "\n"


def compose_base(manifest: dict[str, Any]) -> str:
    project = manifest["project"]
    infra, _, _ = collect_services(manifest)
    network = project.get("network") or normalize_name(project["name"]).replace("-", "_") + "_customer_release"
    lines = [
        "name: ${COMPOSE_PROJECT_NAME:-" + str(project.get("compose_project_name") or normalize_name(project["name"]) + "-customer-release") + "}",
        "",
        "services:",
    ]
    if not infra:
        lines.append("  placeholder:")
        lines.append("    image: busybox:latest")
        lines.append("    command: [\"true\"]")
        lines.append("    networks:")
        lines.append("      - release")
    for item in infra:
        name = str(item["name"])
        item_type = str(item.get("type", "")).lower()
        ports: list[str] = []
        if item.get("host_port") is not None:
            ports.append(f"{env_ref(host_port_var(item))}:{container_port(item)}")
        volumes = [str(v) for v in as_list(item.get("volumes"))]
        volumes.extend(str(v) for v in as_list(item.get("init_sql")))
        service: dict[str, Any] = {
            "image": env_ref(image_var(item)),
            "container_name": "${CONTAINER_PREFIX:-" + normalize_name(project["name"]) + "-release}" + f"-{name}",
            "restart": "unless-stopped",
            "environment": {key: env_ref(key) for key in dict(item.get("env") or {}).keys()} | {"TZ": "${TZ:-Asia/Shanghai}"},
            "networks": ["release"],
        }
        if ports:
            service["ports"] = ports
        if volumes:
            service["volumes"] = volumes
        if item.get("command") is not None:
            service["command"] = item["command"]
        if item.get("healthcheck"):
            service["healthcheck"] = item["healthcheck"]
        elif item_type == "postgres":
            service["healthcheck"] = {
                "test": ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER:-postgres}"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 20,
            }
        elif item_type == "redis":
            service["healthcheck"] = {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 20,
            }
        lines.append(yaml_dump({name: service}, 2))
    lines.extend(
        [
            "",
            "networks:",
            "  release:",
            f"    name: ${{RELEASE_NETWORK:-{network}}}",
            "    driver: bridge",
            "",
        ]
    )
    return "\n".join(lines)


def depends_on_block(names: list[str]) -> dict[str, dict[str, str]]:
    return {name: {"condition": "service_started"} for name in names}


def compose_services(manifest: dict[str, Any]) -> str:
    project = manifest["project"]
    _, services, frontend = collect_services(manifest)
    lines = [
        "x-service-base: &service-base",
        "  restart: unless-stopped",
        "  env_file:",
        "    - ${SERVICE_ENV_FILE:-.env}",
        "  extra_hosts:",
        "    - \"host.docker.internal:host-gateway\"",
        "  networks:",
        "    - release",
        "",
        "services:",
    ]

    if frontend:
        frontend_name = str(frontend.get("name") or "frontend")
        service: dict[str, Any] = {
            "<<": "*service-base",
            "image": env_ref(str(frontend.get("image_var") or "FRONTEND_IMAGE")),
            "container_name": "${CONTAINER_PREFIX:-" + normalize_name(project["name"]) + "-release}" + "-frontend",
            "ports": [f"{env_ref(str(frontend.get('host_port_var') or 'FRONTEND_HOST_PORT'))}:{int(frontend.get('container_port', 80))}"],
            "volumes": [
                f"./{frontend.get('dist_dir', 'frontend/dist')}:/usr/share/nginx/html:ro",
                f"./{frontend.get('nginx_conf', 'frontend/nginx.conf')}:/etc/nginx/conf.d/default.conf:ro",
            ],
            "healthcheck": {
                "test": ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1/"],
                "interval": "20s",
                "timeout": "10s",
                "retries": 10,
            },
        }
        if frontend.get("depends_on"):
            service["depends_on"] = depends_on_block([str(name) for name in as_list(frontend.get("depends_on"))])
        lines.append(yaml_dump({frontend_name: service}, 2))

    for item in services:
        lines.append(yaml_dump({str(item["name"]): service_compose(project, item)}, 2))
        for role in as_list(item.get("roles")):
            if isinstance(role, dict):
                role_data = dict(item)
                role_data["pkg_service_name"] = item["name"]
                role_data.update(role)
                role_data["pkg"] = item.get("pkg")
                role_data["pkg_name"] = item.get("pkg_name")
                lines.append(yaml_dump({str(role_data["name"]): service_compose(project, role_data, expose_port=False)}, 2))

    return "\n".join(lines).replace("<<: '*service-base'", "<<: *service-base") + "\n"


def service_compose(project: dict[str, Any], item: dict[str, Any], expose_port: bool = True) -> dict[str, Any]:
    name = str(item["name"])
    pkg_service_name = str(item.get("pkg_service_name") or name)
    service: dict[str, Any] = {
        "<<": "*service-base",
        "image": env_ref(image_var(item)),
        "container_name": "${CONTAINER_PREFIX:-" + normalize_name(project["name"]) + "-release}" + f"-{name}",
        "environment": dict(item.get("env") or {}) | {"TZ": "${TZ:-Asia/Shanghai}"},
    }
    if expose_port and item.get("host_port") is not None:
        service["ports"] = [f"{env_ref(host_port_var(item))}:{container_port(item)}"]
    if item.get("depends_on"):
        service["depends_on"] = depends_on_block([str(dep) for dep in as_list(item.get("depends_on"))])
    volumes = [str(v) for v in as_list(item.get("volumes"))]
    if item.get("pkg"):
        pkg_source = dict(item)
        pkg_source["name"] = pkg_service_name
        volumes.insert(0, f"./projects/{pkg_service_name}/code/{service_pkg_name(pkg_source)}:/app_code/app.pkg:ro")
    if volumes:
        service["volumes"] = volumes
    if item.get("command") is not None:
        service["command"] = ["/bin/bash", "-c", str(item["command"])]
    if item.get("healthcheck"):
        service["healthcheck"] = item["healthcheck"]
    elif expose_port:
        port = container_port(item)
        path = default_health_path(item)
        service["healthcheck"] = {
            "test": ["CMD-SHELL", f"wget -q -O /dev/null http://127.0.0.1:{port}{path} || curl -fsS http://127.0.0.1:{port}{path} >/dev/null"],
            "interval": "20s",
            "timeout": "10s",
            "retries": 10,
        }
    for key in ("deploy", "devices", "extra_hosts"):
        if key in item:
            service[key] = item[key]
    return service


def release_script(manifest: dict[str, Any]) -> str:
    _, services, frontend = collect_services(manifest)
    service_names = [str(item["name"]) for item in services]
    pkg_service_names = [str(item["name"]) for item in services if item.get("pkg")]
    frontend_name = str((frontend or {}).get("name") or "frontend") if frontend else ""
    service_array = " ".join(json.dumps(name) for name in service_names)
    pkg_service_array = " ".join(json.dumps(name) for name in pkg_service_names)
    frontend_assignment = json.dumps(frontend_name) if frontend else "\"\""
    return f'''#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
ROOT="$(cd "${{SCRIPT_DIR}}/.." && pwd)"
ENV_FILE="${{ROOT}}/.env"
COMPOSE_CMD=()
SERVICES=({service_array})
PKG_SERVICES=({pkg_service_array})
FRONTEND_SERVICE={frontend_assignment}

usage() {{
  cat <<'EOF'
Usage:
  bash scripts/release.sh <command> [args]

Deploy:
  init
  preflight [--skip-pkg] [--skip-images] [--skip-compose-config]
  ports
  images load [dir]
  images save [dir]
  images save-infra [dir]
  images save-all [dir]
  start [--skip-load]
  stop
  down
  reset --yes

Maintain:
  status
  restart <service|all>
  update-pkg <service> <pkg> [--restart]
  migrate
  health <service|all>
  logs <service|all> [--tail N]
EOF
}}

fail() {{
  echo "[release][FAIL] $*" >&2
  exit 1
}}

info() {{
  echo "[release] $*"
}}

find_compose() {{
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
    return 0
  fi
  if docker-compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
    return 0
  fi
  fail "docker compose or docker-compose not found"
}}

compose_run() {{
  find_compose
  (cd "${{ROOT}}" && "${{COMPOSE_CMD[@]}}" -f docker-compose.yml -f docker-compose.services.yml "$@")
}}

compose_infra_run() {{
  find_compose
  (cd "${{ROOT}}" && "${{COMPOSE_CMD[@]}}" -f docker-compose.yml "$@")
}}

load_env() {{
  [ -f "${{ENV_FILE}}" ] || fail "missing ${{ENV_FILE}}, run: bash scripts/release.sh init"
  set -a
  # shellcheck disable=SC1090
  . "${{ENV_FILE}}"
  set +a
}}

service_exists() {{
  local service="$1"
  local item=""
  for item in "${{SERVICES[@]}}"; do
    [ "${{item}}" = "${{service}}" ] && return 0
  done
  [ -n "${{FRONTEND_SERVICE}}" ] && [ "${{service}}" = "${{FRONTEND_SERVICE}}" ] && return 0
  [ "${{service}}" = "frontend" ] && [ -n "${{FRONTEND_SERVICE}}" ] && return 0
  return 1
}}

pkg_name() {{
  case "$1" in
{pkg_name_cases(services)}
    *) printf '%s.pkg\\n' "$1" ;;
  esac
}}

pkg_path() {{
  printf '%s/projects/%s/code/%s\\n' "${{ROOT}}" "$1" "$(pkg_name "$1")"
}}

service_uses_pkg() {{
  local service="$1"
  local item=""
  for item in "${{PKG_SERVICES[@]}}"; do
    [ "${{item}}" = "${{service}}" ] && return 0
  done
  return 1
}}

release_path() {{
  case "$1" in
    /*) printf '%s\\n' "$1" ;;
    *) printf '%s/%s\\n' "${{ROOT}}" "$1" ;;
  esac
}}

compose_roles() {{
  case "$1" in
{compose_roles_cases(services, frontend)}
    *) fail "unknown service: $1" ;;
  esac
}}

all_compose_roles() {{
  local service=""
  [ -n "${{FRONTEND_SERVICE}}" ] && printf '%s\\n' "${{FRONTEND_SERVICE}}"
  for service in "${{SERVICES[@]}}"; do
    compose_roles "${{service}}"
  done
}}

infra_image_list() {{
  load_env
{image_list_lines(manifest, "infra")}
}}

service_image_list() {{
  load_env
{image_list_lines(manifest, "services")}
}}

image_list() {{
  infra_image_list
  service_image_list
}}

safe_image_tar_name() {{
  local image="$1"
  image="${{image//\\//-}}"
  image="${{image//:/-}}"
  printf '%s.tar\\n' "${{image}}"
}}

image_tar_path() {{
  local images_root="$1"
  local image="$2"
  local tar_name=""
  local path=""
  tar_name="$(safe_image_tar_name "${{image}}")"
  for path in "${{images_root}}/${{tar_name}}" "${{images_root}}/infra/${{tar_name}}" "${{images_root}}/services/${{tar_name}}"; do
    if [ -f "${{path}}" ]; then
      printf '%s\\n' "${{path}}"
      return 0
    fi
  done
  return 1
}}

image_id_from_tar() {{
  local tar_file="$1"
  local config_path=""
  local digest=""
  config_path="$(tar -xOf "${{tar_file}}" manifest.json 2>/dev/null | sed -n 's/.*"Config"[[:space:]]*:[[:space:]]*"\\([^"]*\\)".*/\\1/p' | head -n 1)"
  [ -n "${{config_path}}" ] || return 1
  digest="${{config_path#blobs/sha256/}}"
  digest="${{digest%.json}}"
  case "${{digest}}" in
    sha256:*) printf '%s\\n' "${{digest}}" ;;
    *) printf 'sha256:%s\\n' "${{digest}}" ;;
  esac
}}

local_image_id() {{
  docker image inspect --format '{{{{.Id}}}}' "$1" 2>/dev/null || true
}}

sha256_file() {{
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" > "$1.sha256"
  else
    shasum -a 256 "$1" > "$1.sha256"
  fi
}}

init_dirs() {{
  local service=""
  mkdir -p "${{ROOT}}/images/infra" "${{ROOT}}/images/services" "${{ROOT}}/sql" "${{ROOT}}/runtime" "${{ROOT}}/bin" "${{ROOT}}/shared"
  mkdir -p "${{ROOT}}/infra"
{init_dir_lines(manifest)}
  for service in "${{SERVICES[@]}}"; do
    mkdir -p "${{ROOT}}/projects/${{service}}/code" "${{ROOT}}/projects/${{service}}/env"
  done
  if [ ! -f "${{ENV_FILE}}" ]; then
    cp "${{ROOT}}/.env.example" "${{ENV_FILE}}"
    info "created ${{ENV_FILE}}"
  else
    info "${{ENV_FILE}} exists, keeping it"
  fi
}}

host_port_list() {{
  load_env
{host_port_lines(manifest)}
}}

port_in_use() {{
  local port="$1"
  local output=""
  local hex_port=""
  if output="$(ss -H -ltn 2>/dev/null)"; then
    printf '%s\\n' "${{output}}" | awk '{{print $4}}' | sed -n 's/.*:\\([0-9][0-9]*\\)$/\\1/p' | grep -qx "${{port}}"
    return $?
  fi
  hex_port="$(printf '%04X' "${{port}}")"
  awk -v port="${{hex_port}}" '$4 == "0A" {{ split($2, address, ":"); if (toupper(address[2]) == port) found = 1 }} END {{ exit(found ? 0 : 1) }}' /proc/net/tcp /proc/net/tcp6 2>/dev/null
}}

port_owned_by_current_project() {{
  local port="$1"
  local project="${{COMPOSE_PROJECT_NAME:-}}"
  command -v docker >/dev/null 2>&1 || return 1
  docker ps --filter "label=com.docker.compose.project=${{project}}" --format '{{{{.Ports}}}}' 2>/dev/null | grep -Eq "(^|, )[[:alnum:].:_-]+:${{port}}->"
}}

check_host_ports_cmd() {{
  local port=""
  local conflicts=0
  load_env
  while IFS= read -r port; do
    [ -n "${{port}}" ] || continue
    if port_in_use "${{port}}" && ! port_owned_by_current_project "${{port}}"; then
      printf '[release][PORT-CONFLICT] host port is in use by another service: %s\\n' "${{port}}" >&2
      conflicts=1
    fi
  done < <(host_port_list)
  [ "${{conflicts}}" -eq 0 ] || fail "release ports conflict; update *_HOST_PORT in .env"
  info "port check passed"
}}

check_pkg_files() {{
  local service=""
  local path=""
  for service in "${{PKG_SERVICES[@]}}"; do
    path="$(pkg_path "${{service}}")"
    [ -f "${{path}}" ] || fail "missing service pkg: ${{path}}"
  done
}}

check_images() {{
  local image=""
  while IFS= read -r image; do
    [ -n "${{image}}" ] || continue
    docker image inspect "${{image}}" >/dev/null 2>&1 || fail "missing local image: ${{image}}"
  done < <(image_list)
}}

preflight_cmd() {{
  local skip_pkg=0
  local skip_images=0
  local skip_compose_config=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --skip-pkg) skip_pkg=1; shift ;;
      --skip-images) skip_images=1; shift ;;
      --skip-compose-config) skip_compose_config=1; shift ;;
      *) fail "unknown preflight arg: $1" ;;
    esac
  done
  load_env
  check_host_ports_cmd
  [ -f "${{ROOT}}/docker-compose.yml" ] || fail "missing docker-compose.yml"
  [ -f "${{ROOT}}/docker-compose.services.yml" ] || fail "missing docker-compose.services.yml"
{preflight_required_file_lines(manifest)}
  [ "${{skip_pkg}}" -eq 1 ] || check_pkg_files
  [ "${{skip_images}}" -eq 1 ] || check_images
  [ "${{skip_compose_config}}" -eq 1 ] || compose_run config >/dev/null
  info "preflight passed"
}}

load_dir() {{
  local dir="$1"
  local tar_file=""
  [ -d "${{dir}}" ] || return 0
  while IFS= read -r tar_file; do
    [ -n "${{tar_file}}" ] || continue
    info "loading image: ${{tar_file}}"
    docker load -i "${{tar_file}}"
  done < <(find "${{dir}}" -maxdepth 1 -type f -name '*.tar' | sort)
}}

images_load_cmd() {{
  local images_root="${{1:-${{ROOT}}/images}}"
  [ -d "${{images_root}}" ] || fail "image directory does not exist: ${{images_root}}"
  if [ -d "${{images_root}}/infra" ] || [ -d "${{images_root}}/services" ]; then
    load_dir "${{images_root}}/infra"
    load_dir "${{images_root}}/services"
  else
    load_dir "${{images_root}}"
  fi
}}

sync_required_image() {{
  local image="$1"
  local images_root="$2"
  local tar_file=""
  local local_id=""
  local tar_id=""
  tar_file="$(image_tar_path "${{images_root}}" "${{image}}" || true)"
  local_id="$(local_image_id "${{image}}")"
  if [ -z "${{tar_file}}" ]; then
    if [ -n "${{local_id}}" ]; then
      info "local image exists and no tar was provided, skipping: ${{image}}"
      return 0
    fi
    fail "missing local image and offline tar: ${{image}}"
  fi
  tar_id="$(image_id_from_tar "${{tar_file}}" || true)"
  [ -n "${{tar_id}}" ] || fail "cannot read image id from tar: ${{tar_file}}"
  if [ "${{local_id}}" = "${{tar_id}}" ]; then
    info "image already current, skipping: ${{image}}"
    return 0
  fi
  info "loading required image: ${{image}}"
  docker load -i "${{tar_file}}"
}}

sync_required_images_cmd() {{
  local images_root="${{1:-${{ROOT}}/images}}"
  local image=""
  [ -d "${{images_root}}" ] || fail "image directory does not exist: ${{images_root}}"
  while IFS= read -r image; do
    [ -n "${{image}}" ] || continue
    sync_required_image "${{image}}" "${{images_root}}"
  done < <(image_list)
}}

save_image_list() {{
  local output_dir="$1"
  local list_name="$2"
  local image=""
  local output_path=""
  mkdir -p "${{output_dir}}"
  while IFS= read -r image; do
    [ -n "${{image}}" ] || continue
    output_path="${{output_dir}}/$(safe_image_tar_name "${{image}}")"
    info "saving image: ${{image}} -> ${{output_path}}"
    docker save -o "${{output_path}}" "${{image}}"
  done < <("${{list_name}}")
}}

start_cmd() {{
  local skip_load=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --skip-load) skip_load=1; shift ;;
      *) fail "unknown start arg: $1" ;;
    esac
  done
  init_dirs
  if [ "${{skip_load}}" -eq 0 ] && [ -d "${{ROOT}}/images" ]; then
    sync_required_images_cmd "${{ROOT}}/images"
  fi
  preflight_cmd --skip-images
  info "starting infra"
  compose_infra_run up -d --pull never
  info "starting services"
  compose_run up -d --remove-orphans --pull never
}}

stop_cmd() {{
  compose_run stop
}}

down_cmd() {{
  compose_run down --remove-orphans
}}

assert_reset_dir_safe() {{
  local dir="$1"
  [ -n "${{dir}}" ] || fail "reset refuses empty path"
  case "${{dir}}" in
    /|/data|/home|/root|/tmp|/usr|/var|/var/lib|"${{ROOT}}")
      fail "reset refuses broad path: ${{dir}}"
      ;;
  esac
}}

clean_dir_contents() {{
  local dir="$1"
  assert_reset_dir_safe "${{dir}}"
  mkdir -p "${{dir}}"
  info "cleaning runtime data: ${{dir}}"
  find "${{dir}}" -mindepth 1 -maxdepth 1 -exec rm -rf {{}} +
}}

reset_cmd() {{
  [ "${{1:-}}" = "--yes" ] || [ "${{1:-}}" = "-y" ] || fail "reset deletes release runtime data; run: bash scripts/release.sh reset --yes"
  compose_run down --remove-orphans
{reset_dir_lines(manifest)}
  init_dirs
  info "reset complete; deliverables and local Docker images were preserved"
}}

status_cmd() {{
  local service=""
  local path=""
  info "release root: ${{ROOT}}"
  for service in "${{SERVICES[@]}}"; do
    if service_uses_pkg "${{service}}"; then
      path="$(pkg_path "${{service}}")"
      if [ -f "${{path}}" ]; then
        printf '%-24s %s\\n' "${{service}}" "${{path}}"
      else
        printf '%-24s missing: %s\\n' "${{service}}" "${{path}}"
      fi
    else
      printf '%-24s no pkg deployment\\n' "${{service}}"
    fi
  done
  [ -f "${{ENV_FILE}}" ] && command -v docker >/dev/null 2>&1 && compose_run ps || true
}}

restart_cmd() {{
  local target="${{1:-}}"
  local roles=()
  local role=""
  [ -n "${{target}}" ] || fail "restart needs <service|all>"
  if [ "${{target}}" = "all" ]; then
    mapfile -t roles < <(all_compose_roles)
  else
    service_exists "${{target}}" || fail "unknown service: ${{target}}"
    mapfile -t roles < <(compose_roles "${{target}}")
  fi
  for role in "${{roles[@]}}"; do
    info "recreating container: ${{role}}"
    compose_run up -d --force-recreate --no-deps --pull never "${{role}}"
  done
}}

update_pkg_cmd() {{
  local service="${{1:-}}"
  local src_pkg="${{2:-}}"
  local restart_after=0
  local dst_dir=""
  local dst_pkg=""
  [ -n "${{service}}" ] || fail "update-pkg needs <service> <pkg>"
  [ -n "${{src_pkg}}" ] || fail "update-pkg needs <service> <pkg>"
  service_exists "${{service}}" || fail "unknown service: ${{service}}"
  service_uses_pkg "${{service}}" || fail "service does not use pkg deployment: ${{service}}"
  [ -f "${{src_pkg}}" ] || fail "pkg does not exist: ${{src_pkg}}"
  shift 2
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --restart) restart_after=1; shift ;;
      *) fail "unknown update-pkg arg: $1" ;;
    esac
  done
  dst_dir="${{ROOT}}/projects/${{service}}/code"
  dst_pkg="${{dst_dir}}/$(pkg_name "${{service}}")"
  mkdir -p "${{dst_dir}}"
  install -m 644 "${{src_pkg}}" "${{dst_pkg}}.tmp"
  mv "${{dst_pkg}}.tmp" "${{dst_pkg}}"
  sha256_file "${{dst_pkg}}"
  info "updated ${{dst_pkg}}"
  [ "${{restart_after}}" -eq 0 ] || restart_cmd "${{service}}"
}}

migrate_cmd() {{
  load_env
{migration_lines(manifest)}
}}

health_url() {{
  case "$1" in
{health_url_cases(services, frontend)}
    *) fail "unknown service: $1" ;;
  esac
}}

health_one() {{
  local service="$1"
  local url=""
  url="$(health_url "${{service}}")"
  if curl -fsS "${{url}}" >/dev/null; then
    printf '%-24s OK %s\\n' "${{service}}" "${{url}}"
  else
    printf '%-24s FAIL %s\\n' "${{service}}" "${{url}}"
    return 1
  fi
}}

health_cmd() {{
  local target="${{1:-all}}"
  local service=""
  load_env
  if [ "${{target}}" = "all" ]; then
    [ -n "${{FRONTEND_SERVICE}}" ] && health_one "${{FRONTEND_SERVICE}}"
    for service in "${{SERVICES[@]}}"; do health_one "${{service}}"; done
  else
    service_exists "${{target}}" || fail "unknown service: ${{target}}"
    health_one "${{target}}"
  fi
}}

logs_cmd() {{
  local target="${{1:-all}}"
  local tail_lines="200"
  local roles=()
  shift || true
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --tail) [ "$#" -ge 2 ] || fail "--tail needs a value"; tail_lines="$2"; shift 2 ;;
      *) fail "unknown logs arg: $1" ;;
    esac
  done
  if [ "${{target}}" = "all" ]; then
    compose_run logs --tail "${{tail_lines}}" -f
  else
    service_exists "${{target}}" || fail "unknown service: ${{target}}"
    mapfile -t roles < <(compose_roles "${{target}}")
    compose_run logs --tail "${{tail_lines}}" -f "${{roles[@]}}"
  fi
}}

images_cmd() {{
  local sub="${{1:-}}"
  shift || true
  case "${{sub}}" in
    load) images_load_cmd "${{1:-${{ROOT}}/images}}" ;;
    save) save_image_list "${{1:-${{ROOT}}/images/services}}" service_image_list ;;
    save-infra) save_image_list "${{1:-${{ROOT}}/images/infra}}" infra_image_list ;;
    save-all) save_image_list "${{1:-${{ROOT}}/images/infra}}" infra_image_list; save_image_list "${{1:-${{ROOT}}/images/services}}" service_image_list ;;
    *) fail "unknown images subcommand: ${{sub}}" ;;
  esac
}}

main() {{
  local command="${{1:-help}}"
  shift || true
  case "${{command}}" in
    init) [ "$#" -eq 0 ] || fail "init accepts no args"; init_dirs ;;
    preflight) preflight_cmd "$@" ;;
    ports) [ "$#" -eq 0 ] || fail "ports accepts no args"; check_host_ports_cmd ;;
    images) images_cmd "$@" ;;
    start) start_cmd "$@" ;;
    stop) [ "$#" -eq 0 ] || fail "stop accepts no args"; stop_cmd ;;
    down) [ "$#" -eq 0 ] || fail "down accepts no args"; down_cmd ;;
    reset) reset_cmd "$@" ;;
    status) [ "$#" -eq 0 ] || fail "status accepts no args"; status_cmd ;;
    restart) [ "$#" -eq 1 ] || fail "restart needs <service|all>"; restart_cmd "$1" ;;
    update-pkg) update_pkg_cmd "$@" ;;
    migrate) [ "$#" -eq 0 ] || fail "migrate accepts no args"; migrate_cmd ;;
    health) [ "$#" -le 1 ] || fail "health accepts at most one service"; health_cmd "${{1:-all}}" ;;
    logs) logs_cmd "$@" ;;
    help|-h|--help) usage ;;
    *) fail "unknown command: ${{command}}" ;;
  esac
}}

main "$@"
'''


def compose_roles_cases(services: list[dict[str, Any]], frontend: dict[str, Any] | None) -> str:
    lines: list[str] = []
    if frontend:
        name = str(frontend.get("name") or "frontend")
        pattern = "frontend" if name == "frontend" else f"{name}|frontend"
        lines.append(f"    {pattern})")
        lines.append(f"      printf '%s\\n' {json.dumps(name)}")
        lines.append("      ;;")
    for item in services:
        name = str(item["name"])
        roles = [name] + [str(role["name"]) for role in as_list(item.get("roles")) if isinstance(role, dict) and role.get("name")]
        rendered = " ".join(json.dumps(role) for role in roles)
        lines.append(f"    {name})")
        lines.append(f"      printf '%s\\n' {rendered}")
        lines.append("      ;;")
    return "\n".join(lines)


def pkg_name_cases(services: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in services:
        if item.get("pkg") and item.get("pkg_name"):
            lines.append(f"    {item['name']}) printf '%s\\n' {json.dumps(str(item['pkg_name']))} ;;")
    return "\n".join(lines)


def image_list_lines(manifest: dict[str, Any], kind: str) -> str:
    infra, services, frontend = collect_services(manifest)
    items = infra if kind == "infra" else services
    if kind == "infra" and frontend:
        items = items + [frontend]
    vars_ = [image_var(item) if item is not frontend else str(frontend.get("image_var") or "FRONTEND_IMAGE") for item in items]
    if not vars_:
        return "  true"
    joined = " \\\n    ".join(f'"${{{var}:?}}"' for var in vars_)
    return f"  printf '%s\\n' \\\n    {joined}"


def init_dir_lines(manifest: dict[str, Any]) -> str:
    infra, services, frontend = collect_services(manifest)
    dirs = {"${ROOT}/images/infra", "${ROOT}/images/services", "${ROOT}/infra"}
    if frontend:
        dirs.add("${ROOT}/frontend/dist")
        dirs.add("${ROOT}/frontend/desktop")
    for name in as_list(manifest.get("runtime_dirs")):
        dirs.add("${ROOT}/runtime/" + str(name).strip("/"))
    for name in as_list(manifest.get("host_binaries")):
        dirs.add("${ROOT}/bin/" + str(name).strip("/"))
    for item in infra:
        for vol in as_list(item.get("volumes")) + as_list(item.get("init_sql")):
            host = str(vol).split(":", 1)[0]
            if host.startswith("./infra/"):
                dirs.add("${ROOT}/" + host[2:])
    for item in services:
        for vol in as_list(item.get("volumes")):
            host = str(vol).split(":", 1)[0]
            if host.startswith("./infra/"):
                dirs.add("${ROOT}/" + host[2:])
        for role in as_list(item.get("roles")):
            if isinstance(role, dict):
                for vol in as_list(role.get("volumes")):
                    host = str(vol).split(":", 1)[0]
                    if host.startswith("./infra/"):
                        dirs.add("${ROOT}/" + host[2:])
        dirs.add(f"${{ROOT}}/infra/services/{item['name']}/data")
        dirs.add(f"${{ROOT}}/infra/services/{item['name']}/logs")
    for extra in as_list(manifest.get("extra_dirs")):
        dirs.add("${ROOT}/" + str(extra).strip("/"))
    return "\n".join(f"  mkdir -p \"{item}\"" for item in sorted(dirs))


def host_port_lines(manifest: dict[str, Any]) -> str:
    infra, services, frontend = collect_services(manifest)
    vars_: list[str] = []
    for item in infra + services:
        if item.get("host_port") is not None:
            vars_.append(host_port_var(item))
    if frontend:
        vars_.append(str(frontend.get("host_port_var") or "FRONTEND_HOST_PORT"))
    if not vars_:
        return "  true"
    joined = " \\\n    ".join(f'"${{{var}:?}}"' for var in vars_)
    return f"  printf '%s\\n' \\\n    {joined} | sort -n | uniq"


def preflight_required_file_lines(manifest: dict[str, Any]) -> str:
    _, _, frontend = collect_services(manifest)
    lines: list[str] = []
    for name in as_list(manifest.get("sql_files")):
        path = f"${{ROOT}}/sql/{str(name)}"
        lines.append(f'  [ -f "{path}" ] || fail "missing SQL file: {path}"')
    if frontend:
        dist = "${ROOT}/" + str(frontend.get("dist_dir", "frontend/dist")).strip("/")
        nginx = "${ROOT}/" + str(frontend.get("nginx_conf", "frontend/nginx.conf")).strip("/")
        lines.append(f'  [ -f "{dist}/index.html" ] || fail "missing frontend dist: {dist}/index.html"')
        lines.append(f'  [ -f "{nginx}" ] || fail "missing frontend nginx config: {nginx}"')
    return "\n".join(lines)


def reset_dir_lines(manifest: dict[str, Any]) -> str:
    dirs: set[str] = set()
    infra, services, _ = collect_services(manifest)
    for item in infra:
        for vol in as_list(item.get("volumes")):
            host = str(vol).split(":", 1)[0]
            if host.startswith("./infra/"):
                dirs.add("${ROOT}/" + host[2:])
    for item in services:
        dirs.add(f"${{ROOT}}/infra/services/{item['name']}/data")
        dirs.add(f"${{ROOT}}/infra/services/{item['name']}/logs")
        for vol in as_list(item.get("volumes")):
            host = str(vol).split(":", 1)[0]
            if host.startswith("./infra/"):
                dirs.add("${ROOT}/" + host[2:])
        for role in as_list(item.get("roles")):
            if isinstance(role, dict):
                for vol in as_list(role.get("volumes")):
                    host = str(vol).split(":", 1)[0]
                    if host.startswith("./infra/"):
                        dirs.add("${ROOT}/" + host[2:])
    if not dirs:
        return "  info \"no generated runtime data directories to clean\""
    return "\n".join(f'  clean_dir_contents "{path}"' for path in sorted(dirs))


def migration_lines(manifest: dict[str, Any]) -> str:
    command = manifest.get("migration_command")
    if command:
        return f"  {command}"
    return '  info "no migration command configured; edit scripts/release.sh for project-specific migrations"'


def health_url_cases(services: list[dict[str, Any]], frontend: dict[str, Any] | None) -> str:
    lines: list[str] = []
    if frontend:
        name = str(frontend.get("name") or "frontend")
        pattern = "frontend" if name == "frontend" else f"{name}|frontend"
        var = str(frontend.get("host_port_var") or "FRONTEND_HOST_PORT")
        default = frontend.get("host_port", 48100)
        lines.append(f"    {pattern})")
        lines.append(f"      printf 'http://127.0.0.1:%s/\\n' \"${{{var}:-{default}}}\"")
        lines.append("      ;;")
    for item in services:
        var = host_port_var(item)
        default = item.get("host_port", "")
        path = default_health_path(item)
        lines.append(f"    {item['name']})")
        lines.append(f"      printf 'http://127.0.0.1:%s{path}\\n' \"${{{var}:-{default}}}\"")
        lines.append("      ;;")
    return "\n".join(lines)


def readme(manifest: dict[str, Any]) -> str:
    project = manifest["project"]
    infra, services, frontend = collect_services(manifest)
    service_lines = "\n".join(f"- `{item['name']}`: `{item.get('image') or image_var(item)}`" for item in services) or "- none"
    infra_lines = "\n".join(f"- `{item['name']}`: `{item.get('image') or image_var(item)}`" for item in infra) or "- none"
    frontend_line = "- enabled" if frontend else "- disabled"
    return f"""# {project.get('display_name') or project['name']} Release

`release/` is the customer-site deployment directory. Copy this directory to the target server, adjust `.env`, place offline images and packages, then run the scripts below.

## Layout

```text
release/
├── .env.example
├── docker-compose.yml
├── docker-compose.services.yml
├── images/infra/          # offline middleware and low-change images
├── images/services/       # offline business service images
├── projects/<service>/code/
├── frontend/              # static web bundle and nginx config
├── runtime/               # models, SDKs, native libs, licenses
├── sql/                   # init SQL and schema snapshots
├── infra/                 # runtime data, workspaces, logs
├── bin/                   # optional host binaries
└── scripts/release.sh
```

## Infra

{infra_lines}

## Services

{service_lines}

## Frontend

{frontend_line}

## First Deployment

```bash
cd release
bash scripts/release.sh init
# edit .env for server IPs/domains, passwords, ports, images, workers, and runtime paths
bash scripts/release.sh preflight
bash scripts/release.sh start
bash scripts/release.sh migrate
bash scripts/release.sh health all
```

If artifacts are not ready yet, validate the skeleton with:

```bash
bash scripts/release.sh preflight --skip-images --skip-pkg
```

## Required Artifacts

- `images/infra/*.tar`: infra and frontend image tar files.
- `images/services/*.tar`: business service image tar files.
- `projects/<service>/code/<service>.pkg`: service packages when pkg deployment is enabled.
- `frontend/dist/` and `frontend/nginx.conf`: frontend artifacts when frontend is enabled.
- `runtime/`: model, SDK, native-library, or license assets needed at runtime.
- `sql/`: initialization SQL and schema snapshots.

## Maintenance

```bash
bash scripts/release.sh status
bash scripts/release.sh update-pkg <service> /path/to/<service>.pkg --restart
bash scripts/release.sh images save
bash scripts/release.sh images save-infra
bash scripts/release.sh restart <service|all>
bash scripts/release.sh logs <service|all> --tail 300
bash scripts/release.sh stop
bash scripts/release.sh down
bash scripts/release.sh reset --yes
```

`stop` keeps containers and data. `down` removes containers and network but keeps runtime data. `reset --yes` deletes generated runtime data directories only; it preserves `.env`, `images`, `projects`, `runtime`, `frontend`, `bin`, and local Docker images.
"""


def default_nginx_conf() -> str:
    return """server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
"""


def write_placeholders(output: Path, manifest: dict[str, Any]) -> None:
    _, services, frontend = collect_services(manifest)
    for item in services:
        if item.get("pkg"):
            pkg = output / "projects" / str(item["name"]) / "code" / service_pkg_name(item)
            pkg.parent.mkdir(parents=True, exist_ok=True)
            write_text(pkg.parent / ".gitkeep", "")
    for sql_name in as_list(manifest.get("sql_files")):
        write_text(output / "sql" / str(sql_name), f"-- Placeholder for {sql_name}\n")
    if frontend:
        dist = output / str(frontend.get("dist_dir", "frontend/dist"))
        write_text(dist / "index.html", "<!doctype html><title>Release placeholder</title><div id=\"app\"></div>\n")
        write_text(output / str(frontend.get("nginx_conf", "frontend/nginx.conf")), default_nginx_conf())
    for root in ("images/infra", "images/services", "runtime", "bin", "shared", "infra"):
        (output / root).mkdir(parents=True, exist_ok=True)
        write_text(output / root / ".gitkeep", "")


def generate(manifest: dict[str, Any], output: Path, force: bool) -> None:
    ensure_clean_output(output, force)
    write_text(output / "release-manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    write_text(output / ".env.example", env_example(manifest))
    write_text(output / "docker-compose.yml", compose_base(manifest))
    write_text(output / "docker-compose.services.yml", compose_services(manifest))
    write_text(output / "scripts" / "release.sh", release_script(manifest), executable=True)
    write_text(output / "README.md", readme(manifest))
    write_placeholders(output, manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an offline release deployment skeleton from a JSON manifest.")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to release manifest JSON.")
    parser.add_argument("--output", required=True, type=Path, help="Output release directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite output directory if it exists.")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    generate(manifest, args.output, args.force)
    print(f"[generate-release] wrote {args.output}")


if __name__ == "__main__":
    main()

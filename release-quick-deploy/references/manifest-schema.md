# Release Manifest Schema

Use this schema with `scripts/generate_release_package.py`.

## Minimal Example

```json
{
  "project": {
    "name": "demo",
    "display_name": "Demo",
    "compose_project_name": "demo-customer-release",
    "container_prefix": "demo-release",
    "network": "demo_customer_release",
    "timezone": "Asia/Shanghai"
  },
  "infra": [
    {
      "name": "postgres",
      "type": "postgres",
      "image": "postgres:16",
      "image_var": "POSTGRES_IMAGE",
      "host_port": 48300,
      "host_port_var": "POSTGRES_HOST_PORT",
      "env": {
        "POSTGRES_DB": "demo",
        "POSTGRES_USER": "app_user",
        "POSTGRES_PASSWORD": "change-me"
      },
      "volumes": [
        "./infra/postgres/data:/var/lib/postgresql/data"
      ],
      "init_sql": [
        "./sql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro"
      ]
    },
    {
      "name": "redis",
      "type": "redis",
      "image": "redis:7-alpine",
      "image_var": "REDIS_IMAGE",
      "host_port": 48310,
      "host_port_var": "REDIS_HOST_PORT"
    }
  ],
  "services": [
    {
      "name": "api",
      "image": "demo/api-runtime:1.0.0",
      "image_var": "API_IMAGE",
      "host_port": 48200,
      "host_port_var": "API_HOST_PORT",
      "container_port": 8000,
      "pkg": true,
      "pkg_name": "api.pkg",
      "command": "if [ -f /app_code/app.pkg ]; then tar -xzf /app_code/app.pkg -C /app; fi; cd /app; exec python -m gunicorn app.wsgi:application --bind 0.0.0.0:8000",
      "health_path": "/health/",
      "depends_on": ["postgres", "redis"],
      "env": {
        "APP_ENV": "production"
      },
      "volumes": [
        "./infra/services/api/data:/data/api",
        "./infra/services/api/logs:/app/logs"
      ]
    }
  ],
  "frontend": {
    "enabled": true,
    "image": "nginx:1.27-alpine",
    "image_var": "FRONTEND_IMAGE",
    "host_port": 48100,
    "host_port_var": "FRONTEND_HOST_PORT",
    "dist_dir": "frontend/dist",
    "nginx_conf": "frontend/nginx.conf"
  },
  "sql_files": ["init.sql"],
  "runtime_dirs": ["models", "native-libs"],
  "host_binaries": ["aether"]
}
```

## Top-Level Fields

- `project` is required.
- `infra` is optional and lists middleware services.
- `services` is optional and lists business services.
- `frontend` is optional. Set `enabled` to false or omit it when there is no static web frontend.
- `sql_files` creates placeholders under `sql/`.
- `runtime_dirs` creates subdirectories under `runtime/`.
- `host_binaries` creates subdirectories under `bin/` and notes that a separate host manager script may be needed.
- `extra_dirs` creates additional directories relative to release root.
- `post_start_commands` lists commands to show in README and comments; implement them manually in `release.sh` when they must run automatically.
- `migration_command` is a shell command for a project-specific migration. It is written as a placeholder in README; wire it into `release.sh migrate` if needed.

## Infra Service Fields

- `name`: compose service name.
- `type`: optional common type. Supported helpers: `postgres`, `redis`, `rabbitmq`, `minio`, `mysql`. Unknown types fall back to a generic container.
- `image` and `image_var`: image default and env variable name.
- `host_port` and `host_port_var`: host port default and env variable name.
- `container_port`: container port. If omitted, common types use standard ports.
- `env`: env vars and defaults written to `.env.example` and compose.
- `command`: string or list command for compose.
- `volumes`: additional compose volume strings.
- `init_sql`: SQL mount strings added to volumes.
- `healthcheck`: optional object with `test`, `interval`, `timeout`, and `retries`.

## Business Service Fields

- `name`: logical service and default compose role name.
- `image` and `image_var`: runtime image default and env variable name.
- `host_port`, `host_port_var`, `container_port`: port contract.
- `pkg`: when true, create `projects/<name>/code/<pkg_name>` and mount it to `/app_code/app.pkg:ro`.
- `pkg_name`: defaults to `<name>.pkg`.
- `command`: container shell command. Include pkg extraction if the runtime image expects mounted code.
- `health_path`: host health path for `release.sh health`.
- `depends_on`: list of infra or service names.
- `env`: service env vars written into compose. Put site-editable defaults in `.env_defaults` if they should appear in `.env.example`.
- `env_defaults`: additional `.env.example` entries.
- `volumes`: volume strings. Data/log dirs under `infra/services/<name>/...` are created automatically when present.
- `roles`: optional worker roles for the same logical service. Each role can set `name`, `command`, `env`, `volumes`, and `depends_on`. `restart <logical-service>` and `logs <logical-service>` should include all roles.
- `deploy`, `devices`, `extra_hosts`: advanced compose snippets. The generator supports simple lists/dicts, but inspect generated YAML before trusting it for hardware deployments.

## Frontend Fields

- `enabled`: boolean.
- `image`, `image_var`: nginx or static-server image.
- `host_port`, `host_port_var`: host web port.
- `container_port`: defaults to 80.
- `dist_dir`: defaults to `frontend/dist`.
- `nginx_conf`: defaults to `frontend/nginx.conf`.
- `depends_on`: optional list of services.

## After Generation

Always inspect and adapt generated output:

- Add exact health checks for each service.
- Add migrations, tenant initialization, bucket policies, scheduler registration, or cache warmup commands.
- Add hardware-specific compose overrides for GPU/NPU.
- Replace placeholder SQL, frontend index, nginx config, packages, runtime assets, and images.
- Run `bash scripts/release.sh preflight --skip-images --skip-pkg` first, then remove skips once artifacts exist.

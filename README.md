# Guerite

![Keeping guard over your containers](docs/guerite.png)

> _A guerite is a small, enclosed structure used for temporary or makeshift purposes, while a [watchtower](https://github.com/containrrr/watchtower) is a tall, elevated structure used for permanent or sturdy purposes._

Guerite is a [watchtower](https://github.com/containrrr/watchtower) alternative that watches Docker containers that carry a specific label, pulls their base images when updates appear, and restarts the containers, as well as being able to regularly prune stale images.

It provides Pushover and webhook notifications and talks directly to the Docker API, whether local or remote.

## Requirements

- Docker API access (local socket or remote TCP/TLS endpoint)
- Python 3.9+ if running from source; otherwise build the container image
- Optional: Pushover token/user for notifications
- Optional: Webhook URL for JSON notifications

## Image Repository

The official image is available at [ghcr.io/rcarmo/guerite](https://ghcr.io/rcarmo/guerite).

## Build the image

Build from the included Dockerfile:

```bash
docker build -t guerite .
```

### Run against the local socket

```bash
docker run --rm \
	-v /var/run/docker.sock:/var/run/docker.sock:ro \
	-e GUERITE_LOG_LEVEL=INFO \
	guerite:latest
```

### Run against a remote daemon (TLS)

Place `ca.pem`, `cert.pem`, and `key.pem` under `./certs` and point `DOCKER_HOST` to the remote engine:

```bash
docker run --rm \
	-e DOCKER_HOST=tcp://remote-docker-host:2376 \
	-e DOCKER_TLS_VERIFY=1 \
	-e DOCKER_CERT_PATH=/certs \
	-v "$PWD"/certs:/certs:ro \
	guerite:latest
```

## Configuration

Set environment variables to adjust behavior:

- `DOCKER_HOST` (default `unix://var/run/docker.sock`): Docker endpoint to use.
- `GUERITE_UPDATE_LABEL` (default `guerite.update`): Label key containing cron expressions that schedule image update checks.
- `GUERITE_RESTART_LABEL` (default `guerite.restart`): Label key containing cron expressions that schedule forced restarts (without pulling).
- `GUERITE_HEALTH_CHECK_LABEL` (default `guerite.health_check`): Label key containing cron expressions that schedule health checks/restarts.
- `GUERITE_HEALTH_CHECK_BACKOFF_SECONDS` (default `300`): Minimum seconds between health-based restarts per container.
- `GUERITE_PRUNE_CRON` (default unset): Cron expression to periodically prune unused images (non-dangling only). When unset, pruning is skipped.
- `GUERITE_NOTIFICATIONS` (default `update`): Comma-delimited list of events to notify via Pushover/webhook; accepted values: `update`, `restart`, `health`/`health_check`, `startup`, `detect`, `prune`.
- `GUERITE_ROLLBACK_GRACE_SECONDS` (default `3600`): Keep temporary rollback containers/images for at least this many seconds before allowing prune to clean them up.
- `GUERITE_TZ` (default `UTC`): Time zone used to evaluate cron expressions.
- `GUERITE_STATE_FILE` (default `/tmp/guerite_state.json`): Path to persist health backoff state across restarts; file must be writable.
- `GUERITE_DRY_RUN` (default `false`): If `true`, log actions without restarting containers.
- `GUERITE_LOG_LEVEL` (default `INFO`): Log level (e.g., `DEBUG`, `INFO`).
- `GUERITE_PUSHOVER_TOKEN` / `GUERITE_PUSHOVER_USER`: Enable notifications when both are set.
- `GUERITE_PUSHOVER_API` (default `https://api.pushover.net/1/messages.json`): Pushover endpoint override.
- `GUERITE_WEBHOOK_URL` (default unset): If set, sends JSON `{ "title": ..., "message": ... }` POSTs to this URL for enabled events.

## Container labels

Add labels to any container you want Guerite to manage (any label opts the container in):

- `guerite.update=*/10 * * * *` schedules image pull/update checks and restarts when the image changes.
- `guerite.restart=0 3 * * *` schedules forced restarts at the specified cron times (no image pull).
- `guerite.health_check=*/5 * * * *` runs a health check on the cron schedule; if the container is not `healthy`, it is restarted (rate-limited by the backoff).

See `GUERITE_NOTIFICATIONS` for controlling which events generate notifications, and `GUERITE_PRUNE_CRON` for enabling scheduled image pruning.

## Container lifecycle

This section describes what happens to a labeled container over time, from discovery through update/restart, including how names and health checks are handled.

### 1) Discovery and eligibility

- A container is considered "monitored" when it has any of the configured label keys (`guerite.update`, `guerite.restart`, `guerite.health_check`).
- On startup and on each loop, Guerite discovers currently monitored containers.
- When new monitored containers appear, Guerite can emit a "detect" notification (batched to at most one per minute when enabled).
- Swarm-managed containers are skipped (containers created by Docker Swarm services), because recreating them as standalone containers can lose service-managed secrets/configs.

### 2) Scheduling model

- Each label value is a cron expression evaluated in the timezone `GUERITE_TZ`.
- At times when a cron expression matches, Guerite decides whether to take action for that container.
- If an image update is applied for a container on a given run, no additional restart/health actions are performed for that same container in that run (because the container has already been replaced).

### 3) Image update checks (`guerite.update`)

When the update schedule matches:

- Guerite reads the container's image reference (e.g., `repo/name:tag`).
- It pulls that image reference.
- If the pulled image differs from the image currently backing the running container, Guerite performs a replace/recreate (see below).
- If the recreate succeeds, Guerite may remove the old image to keep the host tidy.
- If pulling fails, the container is left untouched and an update notification may be emitted (if enabled).

### 4) Scheduled restarts (`guerite.restart`)

When the restart schedule matches:

- Guerite performs an in-place restart (stop/start) of the existing container.
- No image pull is performed as part of a scheduled restart, and the container is not recreated.

### 5) Health-check restarts (`guerite.health_check`)

When the health-check schedule matches:

- If the container has no Docker healthcheck configured, Guerite skips health-based restarts for that container (and logs a warning).
- If the container started recently, Guerite treats it as being in a grace window and skips the health-based restart attempt.
- If the container is not `healthy` (and not in the grace window), Guerite replaces the container.
- Health-triggered restarts are rate-limited per container for at least `GUERITE_HEALTH_CHECK_BACKOFF_SECONDS`.
- Health backoff state is persisted to `GUERITE_STATE_FILE` so restarts don't flap after Guerite itself restarts.

### 6) Replace/recreate flow (name-preserving)

When Guerite replaces a container (due to an image update or failed health check), it performs a safe "swap" so the original name is preserved:

- The running container is temporarily renamed to `<name>-guerite-old-<suffix>`.
- A new container is created with the same configuration (environment, mounts, ports, labels, network settings, etc.) and a temporary name `<name>-guerite-new-<suffix>`.
- The old container is stopped.
- The new container is renamed back to the original `<name>` and started.
- If the container defines a healthcheck, Guerite waits up to `GUERITE_HEALTH_CHECK_BACKOFF_SECONDS` for the new container to become `healthy`.
  - If the new container does not become healthy in time, Guerite rolls back: it stops/removes the new container and renames/starts the old container back under the original name.
- After a successful swap, the old container is removed.

Notes:

- For replace/recreate operations, the container ID changes (because it is a new container), but the final container name is kept the same.
- If repeated recreate attempts fail, Guerite applies an increasing backoff (up to one hour) before attempting another replace for that container.

### 7) Image pruning lifecycle (optional)

If `GUERITE_PRUNE_CRON` is set, Guerite periodically prunes unused images.

- Pruning is deferred while rollback containers/images exist.
- Rollback containers are kept for at least `GUERITE_ROLLBACK_GRACE_SECONDS` before being eligible for cleanup.
- If pruning fails, it is logged and may generate a notification when enabled.

### 8) Dry-run behavior

If `GUERITE_DRY_RUN=true`, Guerite will not replace/recreate containers. Other non-disruptive parts of the lifecycle (discovery, scheduling, and image pulls for update checks) may still occur.

### 9) Notifications

Guerite can emit notifications as it moves through the lifecycle. Notifications are optional and depend on both configuration and enabled event types.

- Delivery: notifications can be sent via Pushover (when `GUERITE_PUSHOVER_TOKEN` and `GUERITE_PUSHOVER_USER` are set) and/or via a webhook (when `GUERITE_WEBHOOK_URL` is set).
- Enablement: use `GUERITE_NOTIFICATIONS` to choose which event categories should generate notifications. The default is `update`.
- Event categories:
  - `startup`: sent when Guerite starts (if enabled).
  - `detect`: sent when newly monitored containers are discovered; detect notifications are rate-limited and may be batched.
  - `update`: sent when a new image is pulled and a container is successfully replaced; pull failures may also be reported when update notifications are enabled.
  - `restart`: sent for scheduled in-place restarts and restart failures (when enabled).
  - `health` / `health_check`: sent for health-triggered restarts and failures (when enabled).
  - `prune`: sent when scheduled image pruning runs or fails (when enabled).
- Batching: when multiple events happen close together, Guerite may combine them into a single notification message to reduce noise.

## Quick start (local Docker socket)

Use the provided compose file to run Guerite against the local daemon:

```bash
docker compose -f docker-compose.local.yml up -d --build
```

This starts Guerite and a sample `nginx` container labeled for monitoring. The daemon socket is mounted read-only.

## Remote daemon over TCP/TLS

Guerite can talk to a remote Docker host via the standard TLS variables. Prepare TLS client certs from the remote daemon and place them under `./certs` (ca.pem, cert.pem, key.pem). Then run:

```bash
docker compose -f docker-compose.remote.yml up -d --build
```

The compose file sets `DOCKER_HOST=tcp://remote-docker-host:2376`, enables TLS verification, and mounts the certs. Adjust the host name to your environment.

### Using an SSH tunnel instead of exposing TCP

If you prefer an SSH tunnel, forward the remote socket locally and point `DOCKER_HOST` at the local port:

```bash
ssh -N -L 2376:/var/run/docker.sock user@remote-host
DOCKER_HOST=tcp://localhost:2376 DOCKER_TLS_VERIFY=0 docker compose -f docker-compose.remote.yml up -d --build
```

## Running from source

You can run Guerite without containers:

```bash
pip install -e .
python -m guerite
```

Ensure `DOCKER_HOST` and optional Pushover variables are set in the environment.

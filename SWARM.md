# Swarm Support (Investigating)

Swarm mode needs service-aware handling; current code explicitly skips swarm-managed containers to avoid breaking secrets/configs. This document outlines what implementing swarm support would require.

## Key differences
- Target services, not standalone containers: work with ServiceSpec/ServiceID and tasks.
- Recreate via service update: use ServiceUpdate to roll tasks with the new image while preserving the current spec.
- Preserve ServiceSpec fully: TaskTemplate (ContainerSpec, resources, networks, secrets/configs), Update/Rollback configs, placement, constraints, log driver, EndpointSpec.
- Networking: use service networks and EndpointSpec (VIP/dnsrr, published ports); do not container-connect manually.
- Secrets/Configs: keep TaskTemplate.ContainerSpec.{Secrets, Configs} intact.
- Rollouts and backoff: honor UpdateConfig/RollbackConfig; gate updates on task health to prevent flapping.
- Label model: prefer service labels for selection/filtering.
- Prune considerations: avoid deleting images in use by services; be cautious with host-level prune.
- Events and state: watch service/task events; track version index to avoid conflicts; cache current image digest.

## Implementation checklist
- [ ] Add swarm mode detection/flag and skip container recreate path when enabled.
- [ ] List services by label (update/restart/health) instead of containers.
- [ ] Inspect ServiceSpec + Version.Index; cache current image digest to decide updates.
- [ ] Build ServiceUpdate payload mirroring existing spec fields (TaskTemplate, networks, secrets/configs, EndpointSpec, UpdateConfig, RollbackConfig, placement, constraints, log driver).
- [ ] Issue ServiceUpdate with new image ref and current Version.Index; handle 409 conflicts with retry/backoff.
- [ ] Track rollout status via task states/events; gate on task health where possible; surface failures via notifications.
- [ ] Respect UpdateConfig/RollbackConfig semantics (parallelism, delay, failure action, monitor, order); trigger rollback on failure per config.
- [ ] Keep health backoff keyed to service/task template rather than container ID.
- [ ] Adjust prune logic to avoid removing images in use by services.
- [ ] Update README/SPEC to describe swarm support, limitations, and required labels.
- [ ] Add tests/fixtures for service inspection and update flows.

Status: planned/investigating; not implemented yet.

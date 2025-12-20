# Guerite

Guerite is a small Docker container management tool written in Python that watches for changes to the images of running containers with a specific label and pulls and restarts those containers when their base images are updated.

It is inspired by Watchtower but, like a Guerite (a small fortification), it aims to be minimalistic and focused on a specific task without unnecessary complexity.

## Features

- Minimal code base for easy understanding and maintenance.
- Small container footprint (minimal Debian base image with only the required Python runtime).
- Talks to the local Docker daemon directly via the socket.
- Monitors Docker Hub or GitHub Container Registry for updates to base images.
- Notifies users via Pushover when new images are pulled and containers are restarted.
- Configurable via environment variables for Pushover integration.
- Container labels specify:
  - Containers to be monitored are identified by a specific label (e.g., `guerite.monitor=true`).
  - Schedule checks/update times using cron syntax (e.g., `guerite.cron=*/10 * * * *` for every 10 minutes).
  
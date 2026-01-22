# AI Compliance Platform

## Docker socket hardening
The backend no longer mounts the host Docker socket directly. Instead it routes Docker API calls through a limited-privilege proxy (`docker-socket-proxy`). This reduces the risk of container escape, but it is still powerful:

- The proxy exposes only the Docker endpoints enabled in `docker-compose.yml` under `docker-socket-proxy`.
- Keep the proxy service restricted to internal networks and avoid exposing its port to the host.
- Review and further reduce the allowed endpoints if possible.
- Consider moving container orchestration to a dedicated management service or remote Docker API with TLS and RBAC.

If you do not need runtime container control, remove the proxy service and all Docker API usage entirely.

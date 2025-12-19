import docker
from typing import List, Dict, Optional
import os
import httpx
from core.config import settings


class DockerManager:
    """Manages module lifecycle. When running in Cloud Run (`CLOUD_MODE`), Docker operations are disabled and
    module statuses are derived from configured Cloud Run service URLs and their /health endpoints.
    """
    def __init__(self):
        # Try to connect to local Docker only when not in cloud mode
        self.cloud_mode = bool(settings.CLOUD_MODE)
        self.service_url_map = {
            "sentinel-presidio": settings.PRESIDIO_URL,
            "sentinel-toxicity": settings.TOXICITY_URL,
            "sentinel-eu-ai": settings.EU_AI_URL,
        }

        if self.cloud_mode:
            self.client = None
        else:
            try:
                self.client = docker.from_env()
            except Exception as e:
                print(f"Warning: Could not connect to Docker Daemon: {e}")
                self.client = None

    def _probe_health(self, url: str, timeout: float = 3.0) -> bool:
        try:
            r = httpx.get(f"{url.rstrip('/')}/health", timeout=timeout)
            if r.status_code != 200:
                return False
            # Prefer health responses that include an explicit model_loaded flag (for ML modules).
            # If present and False, consider the service unhealthy for our purposes.
            try:
                data = r.json()
                if isinstance(data, dict):
                    if "model_loaded" in data:
                        return bool(data.get("model_loaded"))
                    if "activated" in data:
                        return bool(data.get("activated"))
            except Exception:
                # If parsing JSON fails, fall back to status code check
                pass
            return True
        except Exception:
            return False

    def list_services(self) -> List[Dict]:
        """Lists available compliance modules and their status."""
        services = []
        # Hardcoded list of known modules in docker-compose
        known_modules = [
            {"name": "sentinel-presidio", "display_name": "Presidio PII Scanner"},
            {"name": "sentinel-toxicity", "display_name": "Toxicity Classifier"},
            {"name": "sentinel-eu-ai", "display_name": "EU AI Act Analyzer"},
        ]

        if self.cloud_mode:
            # In Cloud Run mode derive status from configured service URLs
            for module in known_modules:
                name = module["name"]
                display_name = module["display_name"]
                url = self.service_url_map.get(name)
                status = "not_created"
                if url:
                    healthy = self._probe_health(url)
                    status = "running" if healthy else "offline"
                services.append({
                    "name": name,
                    "status": status,
                    "display_name": display_name,
                    "url": url,
                    "start_stop_supported": False
                })
            return services

        # Local (docker) mode
        if not self.client:
            return [
                {"name": module["name"], "status": "unknown", "display_name": module["display_name"], "start_stop_supported": True}
                for module in known_modules
            ]

        for module in known_modules:
            name = module["name"]
            display_name = module["display_name"]
            status = "stopped"
            try:
                container = self.client.containers.get(name)
                status = container.status
            except docker.errors.NotFound:
                status = "not_created"

            services.append({
                "name": name,
                "status": status,
                # Friendly display name
                "display_name": display_name,
                "start_stop_supported": True
            })
        return services

    def start_service(self, service_name: str) -> bool:
        if self.cloud_mode:
            # Start/Stop is not supported in Cloud Run — no-op
            print(f"Start requested for {service_name}, but running in cloud mode — no-op")
            return False

        if not self.client:
            return False
        try:
            container = self.client.containers.get(service_name)
            container.start()
            return True
        except Exception as e:
            print(f"Error starting {service_name}: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        if self.cloud_mode:
            print(f"Stop requested for {service_name}, but running in cloud mode — no-op")
            return False

        if not self.client:
            return False
        try:
            container = self.client.containers.get(service_name)
            container.stop()
            return True
        except Exception as e:
            print(f"Error stopping {service_name}: {e}")
            return False

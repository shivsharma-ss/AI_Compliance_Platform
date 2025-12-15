import docker
from typing import List, Dict, Optional

class DockerManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Warning: Could not connect to Docker Daemon: {e}")
            self.client = None

    def list_services(self) -> List[Dict]:
        """Lists available compliance modules and their status."""
        services = []
        # Hardcoded list of known modules in docker-compose
        known_modules = ["spotixx-presidio", "spotixx-toxicity"]
        
        if not self.client:
            return [{"name": name, "status": "unknown"} for name in known_modules]

        for name in known_modules:
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
                "display_name": name.replace("spotixx-", "").title()
            })
        return services

    def start_service(self, service_name: str) -> bool:
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
        if not self.client:
            return False
        try:
            container = self.client.containers.get(service_name)
            container.stop()
            return True
        except Exception as e:
            print(f"Error stopping {service_name}: {e}")
            return False

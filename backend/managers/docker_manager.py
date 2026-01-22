import docker
from typing import List, Dict, Optional

class DockerManager:
    def __init__(self):
        """
        Initialize the DockerManager by creating a Docker client from the environment.
        
        Attempts to set self.client to a docker client obtained via the environment. If the Docker daemon is unreachable or client creation fails, sets self.client to None and prints a warning containing the error.
        """
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Warning: Could not connect to Docker Daemon: {e}")
            self.client = None

    def list_services(self) -> List[Dict]:
        """
        List available compliance modules and their status.
        
        If the Docker client is unavailable, returns each known module with status "unknown".
        Otherwise, for each known module returns the container's status (e.g., "running", "exited"), "not_created" if the container is absent, or "stopped" as a fallback.
        
        Returns:
            services (List[Dict]): List of service dictionaries with keys:
                - name (str): Module identifier (e.g., "spotixx-presidio").
                - status (str): Current status as described above.
                - display_name (str): Human-friendly name derived from `name`.
        """
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
        """
        Start a Docker container identified by its service (container) name.
        
        Parameters:
            service_name (str): Name of the Docker container to start.
        
        Returns:
            `true` if the container was started successfully, `false` otherwise.
        """
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
        """
        Stop the Docker container identified by the given service name.
        
        Parameters:
            service_name (str): Name of the Docker container to stop.
        
        Returns:
            True if the container was stopped successfully, False otherwise.
        """
        if not self.client:
            return False
        try:
            container = self.client.containers.get(service_name)
            container.stop()
            return True
        except Exception as e:
            print(f"Error stopping {service_name}: {e}")
            return False
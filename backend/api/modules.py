from fastapi import APIRouter, Depends, HTTPException, status
from managers.docker_manager import DockerManager
from api.deps import get_current_user
from models.user import User

router = APIRouter()
docker_manager = DockerManager()

@router.get("/")
def list_modules(current_user: User = Depends(get_current_user)):
    """
    List all available compliance modules and their current status.
    """
    # Authorization: Only Admins can see/manage modules
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return docker_manager.list_services()

@router.post("/{module_name}/start")
def start_module(module_name: str, current_user: User = Depends(get_current_user)):
    """
    Start a compliance module (Docker container).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    success = docker_manager.start_service(module_name)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to start {module_name}")
    
    return {"status": "started", "module": module_name}

@router.post("/{module_name}/stop")
def stop_module(module_name: str, current_user: User = Depends(get_current_user)):
    """
    Stop a compliance module (Docker container).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    success = docker_manager.stop_service(module_name)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to stop {module_name}")
    
    return {"status": "stopped", "module": module_name}

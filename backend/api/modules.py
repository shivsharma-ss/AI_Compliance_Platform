from fastapi import APIRouter, Depends, HTTPException, status
from managers.docker_manager import DockerManager
from api.deps import get_current_user
from models.user import User

router = APIRouter()
docker_manager = DockerManager()

ALLOWED_MODULES = {"spotixx-presidio", "spotixx-toxicity", "spotixx-eu-ai"}

@router.get("/")
def list_modules(current_user: User = Depends(get_current_user)):
    """
    List all available compliance modules and their current status.
    
    Returns:
        A list of modules with their current status (e.g., running, stopped).
    
    Raises:
        HTTPException: 403 if the current user is not an administrator.
    """
    # Authorization: Only Admins can see/manage modules
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return docker_manager.list_services()

@router.post("/{module_name}/start")
def start_module(module_name: str, current_user: User = Depends(get_current_user)):
    """
    Start the specified compliance module (Docker container).
    
    Parameters:
        module_name (str): Name of the module to start.
    
    Returns:
        dict: A payload with keys `"status"` (value `"started"`) and `"module"` (the started module name).
    
    Raises:
        HTTPException: 403 if the current user is not an admin.
        HTTPException: 500 if the module could not be started.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    normalized_name = module_name.strip()
    if normalized_name not in ALLOWED_MODULES:
        raise HTTPException(status_code=400, detail="Invalid module name")
        
    success = docker_manager.start_service(normalized_name)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to start {module_name}")
    
    return {"status": "started", "module": module_name}

@router.post("/{module_name}/stop")
def stop_module(module_name: str, current_user: User = Depends(get_current_user)):
    """
    Stop the specified compliance module container.
    
    Parameters:
        module_name (str): Identifier or name of the module/container to stop.
    
    Returns:
        dict: A payload with keys "status" (the string "stopped") and "module" (the module_name).
    
    Raises:
        HTTPException: 403 if the current user is not authorized (not an admin).
        HTTPException: 500 if the module could not be stopped.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    normalized_name = module_name.strip()
    if normalized_name not in ALLOWED_MODULES:
        raise HTTPException(status_code=400, detail="Invalid module name")
        
    success = docker_manager.stop_service(normalized_name)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to stop {module_name}")
    
    return {"status": "stopped", "module": module_name}
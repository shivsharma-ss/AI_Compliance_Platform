from fastapi import APIRouter, Depends, HTTPException, status
from managers.docker_manager import DockerManager
from api.deps import get_current_user
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models.module import Module

router = APIRouter()
docker_manager = DockerManager()

@router.get("/")
async def list_modules(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    List all available compliance modules and their current status. Available to any authenticated user.
    """
    services = docker_manager.list_services()

    # Fetch persisted enabled flags
    result = await db.execute(select(Module))
    modules_db = {m.name: m for m in result.scalars().all()}

    out = []
    for s in services:
        m = modules_db.get(s["name"])
        enabled = True if m is None else bool(m.enabled)
        out.append({
            "name": s["name"],
            "display_name": s.get("display_name"),
            "status": s.get("status"),
            "url": s.get("url"),
            "enabled": enabled,
            "start_stop_supported": s.get("start_stop_supported", True)
        })
    return out

@router.post("/admin/{module_name}")
async def set_module_enabled(module_name: str, payload: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Admin-only: enable or disable a module for evaluations (persisted)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    if "enabled" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'enabled' in payload")

    enabled = bool(payload.get("enabled"))

    result = await db.execute(select(Module).where(Module.name == module_name))
    module = result.scalars().first()
    if not module:
        module = Module(name=module_name, display_name=module_name, enabled=enabled)
        db.add(module)
    else:
        module.enabled = enabled

    await db.commit()
    await db.refresh(module)
    return {"name": module.name, "enabled": module.enabled}

@router.post("/{module_name}/start")
def start_module(module_name: str, current_user: User = Depends(get_current_user)):
    """
    Start a compliance module (Docker container).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    # In cloud mode start/stop is not supported — provide a friendly message
    from core.config import settings
    if settings.CLOUD_MODE:
        raise HTTPException(status_code=400, detail="Operation not supported in cloud mode. Modules are managed by Cloud Run and cannot be started/stopped via Docker operations.")
        
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

    from core.config import settings
    if settings.CLOUD_MODE:
        raise HTTPException(status_code=400, detail="Operation not supported in cloud mode. Modules are managed by Cloud Run and cannot be started/stopped via Docker operations.")
        
    success = docker_manager.stop_service(module_name)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to stop {module_name}")
    
    return {"status": "stopped", "module": module_name}

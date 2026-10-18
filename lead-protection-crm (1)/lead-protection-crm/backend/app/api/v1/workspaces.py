from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_workspace, require_owner
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceOut, WorkspaceUpdate
from app.data_access.workspace_repo import workspace_repo
from app.business_rules.permission_rules import permission_rules

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

@router.get("/current", response_model=WorkspaceOut)
def get_workspace_details(current_workspace: Workspace = Depends(get_current_workspace)):
    """
    Get current workspace details for the authenticated user.
    """
    return current_workspace

@router.put("/current", response_model=WorkspaceOut)
def update_workspace_details(
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """
    Update workspace name or lead engine configuration settings (Owner only).
    """
    updated_workspace = workspace_repo.update(
        db=db,
        workspace=current_workspace,
        name=payload.name,
        settings=payload.settings
    )
    return updated_workspace

@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace_by_id(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Direct access to a workspace by ID.
    Enforces strict workspace isolation: A user cannot read another workspace's data,
    even by guessing IDs.
    """
    permission_rules.enforce_workspace_isolation(current_user, workspace_id)
    workspace = workspace_repo.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace

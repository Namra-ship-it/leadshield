from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.custom_field import CustomFieldOut, CustomFieldCreate
from app.data_access.custom_field_repo import custom_field_repo

router = APIRouter(prefix="/custom-fields", tags=["Custom Fields"])

@router.get("", response_model=List[CustomFieldOut])
def list_custom_fields(
    entity_type: Optional[str] = Query(None, pattern="^(contact|opportunity|company)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all custom fields defined for the current workspace.
    """
    return custom_field_repo.list_by_workspace(
        db=db,
        workspace_id=current_user.workspace_id,
        entity_type=entity_type
    )

@router.post("", response_model=CustomFieldOut, status_code=status.HTTP_201_CREATED)
def create_custom_field(
    payload: CustomFieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Add a custom field to the workspace (Admin or Owner only).
    """
    return custom_field_repo.create(
        db=db,
        workspace_id=current_user.workspace_id,
        entity_type=payload.entity_type,
        label=payload.label,
        field_key=payload.field_key,
        field_type=payload.field_type,
        options=payload.options
    )

@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_field(
    field_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a custom field definition (Admin or Owner only).
    """
    field_def = custom_field_repo.get_by_id(db, field_id, current_user.workspace_id)
    if not field_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom field not found")
    custom_field_repo.delete(db, field_def)
    return None

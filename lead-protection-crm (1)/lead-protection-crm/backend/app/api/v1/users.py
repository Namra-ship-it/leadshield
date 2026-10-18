from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User, UserRole
from app.schemas.user import UserOut, UserCreate, UserUpdate, UserRoleUpdate, UserStatusUpdate
from app.data_access.user_repo import user_repo
from app.business_rules.permission_rules import permission_rules
from app.core.security import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("", response_model=List[UserOut])
def list_workspace_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all team members belonging strictly to the current user's workspace.
    """
    return user_repo.list_by_workspace(db, current_user.workspace_id)

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_workspace_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new user in the current workspace (Admin or Owner only).
    """
    # Check if creating an Owner (only an Owner can create another Owner)
    if payload.role == UserRole.OWNER and current_user.role != UserRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an Owner can create another Owner."
        )

    # Check if email is already taken in this workspace
    existing_user = user_repo.get_by_email(db, payload.email, workspace_id=current_user.workspace_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in this workspace."
        )

    hashed_pw = get_password_hash(payload.password)
    user = user_repo.create(
        db=db,
        workspace_id=current_user.workspace_id,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hashed_pw,
        role=payload.role,
        phone=payload.phone,
        telegram_chat_id=payload.telegram_chat_id
    )
    return user

@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user details. Enforces strict workspace isolation:
    Cannot get users from another workspace even by guessing user_id.
    """
    user = user_repo.get_by_id(db, user_id=user_id, workspace_id=current_user.workspace_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this workspace."
        )
    return user

@router.patch("/{user_id}", response_model=UserOut)
def update_user_profile(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user profile. A user can update their own profile;
    Admins and Owners can update any member in the workspace.
    """
    target_user = user_repo.get_by_id(db, user_id=user_id, workspace_id=current_user.workspace_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if current_user.id != target_user.id and current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    updated_user = user_repo.update(
        db=db,
        user=target_user,
        full_name=payload.full_name,
        phone=payload.phone,
        telegram_chat_id=payload.telegram_chat_id,
        status=payload.status
    )
    return updated_user

@router.patch("/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update a user's role (Owner or Admin subject to permission checks).
    """
    target_user = user_repo.get_by_id(db, user_id=user_id, workspace_id=current_user.workspace_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    permission_rules.can_manage_user_role(current_user, target_user, payload.role)

    updated_user = user_repo.update(db=db, user=target_user, role=payload.role)
    return updated_user

@router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Quickly toggle employee availability status (Available, Busy, On leave, Offline).
    A user can change their own status; Admin/Owner can change any member's status.
    """
    target_user = user_repo.get_by_id(db, user_id=user_id, workspace_id=current_user.workspace_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if current_user.id != target_user.id and current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    updated_user = user_repo.update(db=db, user=target_user, status=payload.status)

    # Reassign leads immediately if employee goes on leave
    from app.business_rules.lead_engine_rules import lead_engine_rules
    lead_engine_rules.handle_user_status_change(db, updated_user, payload.status)

    return updated_user

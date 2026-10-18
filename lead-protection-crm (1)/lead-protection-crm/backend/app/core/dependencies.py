from typing import List, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.data_access.user_repo import user_repo
from app.data_access.workspace_repo import workspace_repo
from app.business_rules.permission_rules import permission_rules

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    workspace_id: str = payload.get("workspace_id")
    if user_id is None or workspace_id is None:
        raise credentials_exception

    user = user_repo.get_by_id(db, user_id=user_id, workspace_id=workspace_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user

def get_current_workspace(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Workspace:
    workspace = workspace_repo.get_by_id(db, current_user.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    return workspace

class RoleChecker:
    def __init__(self, allowed_roles: List[Union[UserRole, str]]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        permission_rules.require_roles(current_user, self.allowed_roles)
        return current_user

require_owner = RoleChecker([UserRole.OWNER])
require_admin = RoleChecker([UserRole.OWNER, UserRole.ADMIN])
require_any_user = RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.USER])

from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole, EmployeeStatus
from app.models.workspace import Workspace
from app.schemas.user import UserSignup
from app.data_access.workspace_repo import workspace_repo
from app.data_access.user_repo import user_repo
from app.core.security import verify_password, get_password_hash, create_access_token

class AuthRules:
    @staticmethod
    def register_workspace_and_owner(db: Session, signup_data: UserSignup) -> Tuple[Workspace, User, str]:
        # Check if user with this email already exists globally or in a workspace
        existing_user = user_repo.get_by_email(db, signup_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        # 1. Create Workspace
        workspace = workspace_repo.create(
            db=db,
            name=signup_data.workspace_name
        )

        # 2. Hash password with Argon2
        hashed_pw = get_password_hash(signup_data.password)

        # 3. Create User with OWNER role
        user = user_repo.create(
            db=db,
            workspace_id=workspace.id,
            email=signup_data.email,
            full_name=signup_data.full_name,
            hashed_password=hashed_pw,
            role=UserRole.OWNER,
            status=EmployeeStatus.AVAILABLE
        )

        # 4. Generate JWT access token
        access_token = create_access_token(
            subject=user.id,
            extra_data={
                "workspace_id": workspace.id,
                "role": user.role,
                "email": user.email
            }
        )

        return workspace, user, access_token

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        user = user_repo.get_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        return user

auth_rules = AuthRules()

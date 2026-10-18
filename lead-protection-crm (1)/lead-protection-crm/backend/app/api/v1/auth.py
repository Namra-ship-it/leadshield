from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserSignup, UserLogin, UserOut
from app.schemas.workspace import WorkspaceOut
from app.schemas.token import Token
from app.business_rules.auth_rules import auth_rules
from app.core.security import create_access_token
from app.core.dependencies import get_current_user, get_current_workspace
from app.models.user import User
from app.models.workspace import Workspace

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(payload: UserSignup, db: Session = Depends(get_db)):
    """
    Creates a new workspace and sets the user as Owner with Argon2 hashed password.
    """
    workspace, user, access_token = auth_rules.register_workspace_and_owner(db, payload)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        workspace=WorkspaceOut.model_validate(workspace)
    )

@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates user and returns JWT access token with workspace context.
    """
    user = auth_rules.authenticate_user(db, payload.email, payload.password)
    access_token = create_access_token(
        subject=user.id,
        extra_data={
            "workspace_id": user.workspace_id,
            "role": user.role,
            "email": user.email
        }
    )
    workspace = user.workspace
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        workspace=WorkspaceOut.model_validate(workspace)
    )

@router.get("/me")
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """
    Returns current authenticated user details and their workspace.
    """
    return {
        "user": UserOut.model_validate(current_user),
        "workspace": WorkspaceOut.model_validate(current_workspace)
    }

from typing import Optional
from pydantic import BaseModel
from app.schemas.user import UserOut
from app.schemas.workspace import WorkspaceOut

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    workspace: WorkspaceOut

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    workspace_id: Optional[str] = None
    role: Optional[str] = None

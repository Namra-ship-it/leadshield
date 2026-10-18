from typing import List, Union
from fastapi import HTTPException, status
from app.models.user import User, UserRole

class PermissionRules:
    @staticmethod
    def enforce_workspace_isolation(user: User, resource_workspace_id: str) -> None:
        """
        Enforce that the requesting user's workspace strictly matches the target resource's workspace.
        Even if an attacker guesses a valid UUID/ID of another workspace or its resources,
        access is blocked with 403 Forbidden or 404 Not Found.
        """
        if user.workspace_id != resource_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Resource belongs to a different workspace."
            )

    @staticmethod
    def require_roles(user: User, allowed_roles: List[Union[UserRole, str]]) -> None:
        """
        Enforce that the user has one of the allowed roles.
        """
        allowed_str = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]
        if user.role not in allowed_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Requires one of the following roles: {', '.join(allowed_str)}."
            )

    @staticmethod
    def can_manage_user_role(actor: User, target: User, target_new_role: UserRole) -> None:
        """
        Only Owner can promote to Owner or change Owner's role.
        Admin can manage regular Users, but cannot modify an Owner or make someone Owner.
        Regular User cannot modify roles at all.
        """
        if actor.role == UserRole.USER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users cannot modify roles."
            )

        if actor.role == UserRole.ADMIN.value:
            if target.role == UserRole.OWNER.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot modify an Owner."
                )
            if target_new_role == UserRole.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot promote anyone to Owner."
                )

permission_rules = PermissionRules()

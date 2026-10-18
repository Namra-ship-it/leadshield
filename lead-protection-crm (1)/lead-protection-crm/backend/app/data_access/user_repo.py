from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User, UserRole, EmployeeStatus
from app.core.phone import normalize_phone_e164

class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: str, workspace_id: Optional[str] = None) -> Optional[User]:
        query = db.query(User).filter(User.id == user_id)
        if workspace_id is not None:
            # Enforce strict workspace isolation
            query = query.filter(User.workspace_id == workspace_id)
        return query.first()

    @staticmethod
    def get_by_email(db: Session, email: str, workspace_id: Optional[str] = None) -> Optional[User]:
        query = db.query(User).filter(User.email == email.lower().strip())
        if workspace_id is not None:
            query = query.filter(User.workspace_id == workspace_id)
        return query.first()

    @staticmethod
    def list_by_workspace(db: Session, workspace_id: str) -> List[User]:
        return db.query(User).filter(User.workspace_id == workspace_id).order_by(User.created_at.asc()).all()

    @staticmethod
    def create(
        db: Session,
        workspace_id: str,
        email: str,
        full_name: str,
        hashed_password: str,
        role: UserRole = UserRole.USER,
        status: EmployeeStatus = EmployeeStatus.AVAILABLE,
        phone: Optional[str] = None,
        telegram_chat_id: Optional[str] = None
    ) -> User:
        user = User(
            workspace_id=workspace_id,
            email=email.lower().strip(),
            full_name=full_name.strip(),
            hashed_password=hashed_password,
            role=role.value if isinstance(role, UserRole) else str(role),
            status=status.value if isinstance(status, EmployeeStatus) else str(status),
            is_active=True,
            phone=normalize_phone_e164(phone) if phone else None,
            telegram_chat_id=telegram_chat_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update(
        db: Session,
        user: User,
        full_name: Optional[str] = None,
        role: Optional[UserRole] = None,
        status: Optional[EmployeeStatus] = None,
        is_active: Optional[bool] = None,
        phone: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        hashed_password: Optional[str] = None
    ) -> User:
        if full_name is not None:
            user.full_name = full_name.strip()
        if role is not None:
            user.role = role.value if isinstance(role, UserRole) else str(role)
        if status is not None:
            user.status = status.value if isinstance(status, EmployeeStatus) else str(status)
        if is_active is not None:
            user.is_active = is_active
        if phone is not None:
            user.phone = normalize_phone_e164(phone) if phone else None
        if telegram_chat_id is not None:
            user.telegram_chat_id = telegram_chat_id
        if hashed_password is not None:
            user.hashed_password = hashed_password
            
        db.commit()
        db.refresh(user)
        return user

user_repo = UserRepository()

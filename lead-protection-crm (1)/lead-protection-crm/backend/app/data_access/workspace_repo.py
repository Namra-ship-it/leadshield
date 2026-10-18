import re
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.workspace import Workspace

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text or "workspace"

class WorkspaceRepository:
    @staticmethod
    def get_by_id(db: Session, workspace_id: str) -> Optional[Workspace]:
        return db.query(Workspace).filter(Workspace.id == workspace_id).first()

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[Workspace]:
        return db.query(Workspace).filter(Workspace.slug == slug).first()

    @staticmethod
    def create(db: Session, name: str, slug: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> Workspace:
        base_slug = slugify(slug if slug else name)
        final_slug = base_slug
        counter = 1
        while db.query(Workspace).filter(Workspace.slug == final_slug).first() is not None:
            final_slug = f"{base_slug}-{counter}"
            counter += 1

        workspace = Workspace(
            name=name,
            slug=final_slug,
            settings=settings if settings is not None else {
                "acknowledgement_timeout_seconds": 300,
                "escalation_backup_timeout_seconds": 300,
                "escalation_manager_timeout_seconds": 300,
                "max_open_leads_per_rep": 5,
                "auto_assign_enabled": True
            }
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return workspace

    @staticmethod
    def update(db: Session, workspace: Workspace, name: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> Workspace:
        if name is not None:
            workspace.name = name
        if settings is not None:
            # Merge settings
            current_settings = dict(workspace.settings or {})
            current_settings.update(settings)
            workspace.settings = current_settings
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(workspace, "settings")
            
        db.commit()
        db.refresh(workspace)
        return workspace

workspace_repo = WorkspaceRepository()

from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.custom_field import CustomFieldDefinition, slugify_key

class CustomFieldRepository:
    @staticmethod
    def list_by_workspace(db: Session, workspace_id: str, entity_type: Optional[str] = None) -> List[CustomFieldDefinition]:
        query = db.query(CustomFieldDefinition).filter(CustomFieldDefinition.workspace_id == workspace_id)
        if entity_type:
            query = query.filter(CustomFieldDefinition.entity_type == entity_type)
        return query.order_by(CustomFieldDefinition.created_at.asc()).all()

    @staticmethod
    def get_by_id(db: Session, field_id: str, workspace_id: str) -> Optional[CustomFieldDefinition]:
        return db.query(CustomFieldDefinition).filter(
            CustomFieldDefinition.id == field_id,
            CustomFieldDefinition.workspace_id == workspace_id
        ).first()

    @staticmethod
    def get_by_key(db: Session, workspace_id: str, entity_type: str, field_key: str) -> Optional[CustomFieldDefinition]:
        return db.query(CustomFieldDefinition).filter(
            CustomFieldDefinition.workspace_id == workspace_id,
            CustomFieldDefinition.entity_type == entity_type,
            CustomFieldDefinition.field_key == field_key
        ).first()

    @staticmethod
    def create(
        db: Session,
        workspace_id: str,
        entity_type: str,
        label: str,
        field_key: Optional[str] = None,
        field_type: str = "text",
        options: Optional[List[str]] = None
    ) -> CustomFieldDefinition:
        final_key = slugify_key(field_key if field_key else label)
        
        # Ensure key is unique in this workspace + entity_type
        base_key = final_key
        counter = 1
        while db.query(CustomFieldDefinition).filter(
            CustomFieldDefinition.workspace_id == workspace_id,
            CustomFieldDefinition.entity_type == entity_type,
            CustomFieldDefinition.field_key == final_key
        ).first() is not None:
            final_key = f"{base_key}_{counter}"
            counter += 1

        field_def = CustomFieldDefinition(
            workspace_id=workspace_id,
            entity_type=entity_type,
            label=label.strip(),
            field_key=final_key,
            field_type=field_type,
            options=options or []
        )
        db.add(field_def)
        db.commit()
        db.refresh(field_def)
        return field_def

    @staticmethod
    def delete(db: Session, field_def: CustomFieldDefinition) -> None:
        db.delete(field_def)
        db.commit()

custom_field_repo = CustomFieldRepository()

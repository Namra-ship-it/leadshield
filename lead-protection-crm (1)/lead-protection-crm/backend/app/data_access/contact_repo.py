from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.contact import Contact
from app.core.phone import normalize_phone_e164

class ContactRepository:
    @staticmethod
    def list_by_workspace(db: Session, workspace_id: str) -> List[Contact]:
        return db.query(Contact).filter(Contact.workspace_id == workspace_id).order_by(Contact.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, contact_id: str, workspace_id: str) -> Optional[Contact]:
        return db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.workspace_id == workspace_id
        ).first()

    @staticmethod
    def get_by_phone(db: Session, phone: str, workspace_id: Optional[str] = None) -> Optional[Contact]:
        if not phone:
            return None
        norm = normalize_phone_e164(phone)
        raw = str(phone).strip()
        query = db.query(Contact)
        if workspace_id is not None:
            query = query.filter(Contact.workspace_id == workspace_id)
        conditions = [Contact.phone == raw]
        if norm:
            conditions.append(Contact.phone == norm)
        return query.filter(or_(*conditions)).first()

    @staticmethod
    def create(
        db: Session,
        workspace_id: str,
        full_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company_id: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Contact:
        normalized_phone = normalize_phone_e164(phone) if phone else None
        contact = Contact(
            workspace_id=workspace_id,
            full_name=full_name.strip(),
            email=email.strip().lower() if email else None,
            phone=normalized_phone,
            company_id=company_id,
            custom_fields=custom_fields or {}
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def update(
        db: Session,
        contact: Contact,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company_id: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Contact:
        if full_name is not None:
            contact.full_name = full_name.strip()
        if email is not None:
            contact.email = email.strip().lower() if email else None
        if phone is not None:
            contact.phone = normalize_phone_e164(phone) if phone else None
        if company_id is not None:
            contact.company_id = company_id
        if custom_fields is not None:
            updated_fields = dict(contact.custom_fields or {})
            updated_fields.update(custom_fields)
            contact.custom_fields = updated_fields
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(contact, "custom_fields")

        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def delete(db: Session, contact: Contact) -> None:
        db.delete(contact)
        db.commit()

contact_repo = ContactRepository()

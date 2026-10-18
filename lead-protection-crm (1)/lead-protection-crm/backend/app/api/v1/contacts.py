from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.contact import ContactOut, ContactCreate, ContactUpdate
from app.data_access.contact_repo import contact_repo
from app.business_rules.crm_rules import crm_rules

router = APIRouter(prefix="/contacts", tags=["Contacts"])

@router.get("", response_model=List[ContactOut])
def list_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return contact_repo.list_by_workspace(db, current_user.workspace_id)

@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    crm_rules.validate_contact_company(db, current_user.workspace_id, payload.company_id)
    return contact_repo.create(
        db=db,
        workspace_id=current_user.workspace_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        company_id=payload.company_id,
        custom_fields=payload.custom_fields
    )

@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = contact_repo.get_by_id(db, contact_id, current_user.workspace_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact

@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: str,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = contact_repo.get_by_id(db, contact_id, current_user.workspace_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    if payload.company_id is not None:
        crm_rules.validate_contact_company(db, current_user.workspace_id, payload.company_id)

    return contact_repo.update(
        db=db,
        contact=contact,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        company_id=payload.company_id,
        custom_fields=payload.custom_fields
    )

@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    contact = contact_repo.get_by_id(db, contact_id, current_user.workspace_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    contact_repo.delete(db, contact)
    return None

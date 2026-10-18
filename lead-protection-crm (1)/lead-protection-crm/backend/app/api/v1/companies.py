from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.company import CompanyOut, CompanyCreate, CompanyUpdate
from app.data_access.company_repo import company_repo

router = APIRouter(prefix="/companies", tags=["Companies"])

@router.get("", response_model=List[CompanyOut])
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return company_repo.list_by_workspace(db, current_user.workspace_id)

@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return company_repo.create(
        db=db,
        workspace_id=current_user.workspace_id,
        name=payload.name,
        domain=payload.domain,
        custom_fields=payload.custom_fields
    )

@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = company_repo.get_by_id(db, company_id, current_user.workspace_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company

@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: str,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = company_repo.get_by_id(db, company_id, current_user.workspace_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company_repo.update(
        db=db,
        company=company,
        name=payload.name,
        domain=payload.domain,
        custom_fields=payload.custom_fields
    )

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    company = company_repo.get_by_id(db, company_id, current_user.workspace_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    company_repo.delete(db, company)
    return None

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.company import Company

class CompanyRepository:
    @staticmethod
    def list_by_workspace(db: Session, workspace_id: str) -> List[Company]:
        return db.query(Company).filter(Company.workspace_id == workspace_id).order_by(Company.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, company_id: str, workspace_id: str) -> Optional[Company]:
        return db.query(Company).filter(
            Company.id == company_id,
            Company.workspace_id == workspace_id
        ).first()

    @staticmethod
    def create(
        db: Session,
        workspace_id: str,
        name: str,
        domain: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Company:
        company = Company(
            workspace_id=workspace_id,
            name=name.strip(),
            domain=domain.strip() if domain else None,
            custom_fields=custom_fields or {}
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    @staticmethod
    def update(
        db: Session,
        company: Company,
        name: Optional[str] = None,
        domain: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Company:
        if name is not None:
            company.name = name.strip()
        if domain is not None:
            company.domain = domain.strip()
        if custom_fields is not None:
            updated_fields = dict(company.custom_fields or {})
            updated_fields.update(custom_fields)
            company.custom_fields = updated_fields
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(company, "custom_fields")

        db.commit()
        db.refresh(company)
        return company

    @staticmethod
    def delete(db: Session, company: Company) -> None:
        db.delete(company)
        db.commit()

company_repo = CompanyRepository()

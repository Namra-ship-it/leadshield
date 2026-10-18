from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.data_access.contact_repo import contact_repo
from app.data_access.company_repo import company_repo
from app.data_access.user_repo import user_repo
from app.models.opportunity import PipelineStage

class CRMRules:
    @staticmethod
    def validate_opportunity_relations(
        db: Session,
        workspace_id: str,
        contact_id: Optional[str] = None,
        company_id: Optional[str] = None,
        assigned_to_id: Optional[str] = None
    ) -> None:
        """
        Enforce that referenced Contact, Company, and Assigned User strictly
        belong to the same workspace (prevent cross-tenant linkage!).
        """
        if contact_id is not None:
            contact = contact_repo.get_by_id(db, contact_id, workspace_id)
            if not contact:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Referenced contact does not exist in this workspace."
                )

        if company_id is not None:
            company = company_repo.get_by_id(db, company_id, workspace_id)
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Referenced company does not exist in this workspace."
                )

        if assigned_to_id is not None:
            user = user_repo.get_by_id(db, assigned_to_id, workspace_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Assigned user does not exist in this workspace."
                )

    @staticmethod
    def validate_contact_company(db: Session, workspace_id: str, company_id: Optional[str]) -> None:
        if company_id is not None:
            company = company_repo.get_by_id(db, company_id, workspace_id)
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Referenced company does not exist in this workspace."
                )

crm_rules = CRMRules()

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.opportunity import (
    OpportunityOut,
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityStageUpdate
)
from app.data_access.opportunity_repo import opportunity_repo
from app.business_rules.crm_rules import crm_rules

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])

@router.get("", response_model=List[OpportunityOut])
def list_opportunities(
    stage: Optional[str] = Query(None),
    assigned_to_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return opportunity_repo.list_by_workspace(
        db=db,
        workspace_id=current_user.workspace_id,
        stage=stage,
        assigned_to_id=assigned_to_id
    )

@router.post("", response_model=OpportunityOut, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    payload: OpportunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    crm_rules.validate_opportunity_relations(
        db=db,
        workspace_id=current_user.workspace_id,
        contact_id=payload.contact_id,
        company_id=payload.company_id,
        assigned_to_id=payload.assigned_to_id
    )
    return opportunity_repo.create(
        db=db,
        workspace_id=current_user.workspace_id,
        title=payload.title,
        value=payload.value,
        currency=payload.currency,
        stage=payload.stage,
        contact_id=payload.contact_id,
        company_id=payload.company_id,
        assigned_to_id=payload.assigned_to_id,
        custom_fields=payload.custom_fields
    )

@router.get("/{opportunity_id}", response_model=OpportunityOut)
def get_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    opp = opportunity_repo.get_by_id(db, opportunity_id, current_user.workspace_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return opp

@router.patch("/{opportunity_id}/stage", response_model=OpportunityOut)
def update_opportunity_stage(
    opportunity_id: str,
    payload: OpportunityStageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Move opportunity across pipeline board stages.
    """
    opp = opportunity_repo.get_by_id(db, opportunity_id, current_user.workspace_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    return opportunity_repo.update_stage(db, opp, payload.stage)

@router.patch("/{opportunity_id}", response_model=OpportunityOut)
def update_opportunity(
    opportunity_id: str,
    payload: OpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    opp = opportunity_repo.get_by_id(db, opportunity_id, current_user.workspace_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    crm_rules.validate_opportunity_relations(
        db=db,
        workspace_id=current_user.workspace_id,
        contact_id=payload.contact_id,
        company_id=payload.company_id,
        assigned_to_id=payload.assigned_to_id
    )

    return opportunity_repo.update(
        db=db,
        opportunity=opp,
        title=payload.title,
        value=payload.value,
        currency=payload.currency,
        stage=payload.stage,
        contact_id=payload.contact_id,
        company_id=payload.company_id,
        assigned_to_id=payload.assigned_to_id,
        custom_fields=payload.custom_fields
    )

@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    opp = opportunity_repo.get_by_id(db, opportunity_id, current_user.workspace_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    opportunity_repo.delete(db, opp)
    return None

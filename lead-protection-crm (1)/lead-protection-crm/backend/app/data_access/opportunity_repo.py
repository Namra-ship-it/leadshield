from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.opportunity import Opportunity, PipelineStage

class OpportunityRepository:
    @staticmethod
    def list_by_workspace(
        db: Session,
        workspace_id: str,
        stage: Optional[str] = None,
        assigned_to_id: Optional[str] = None
    ) -> List[Opportunity]:
        query = db.query(Opportunity).filter(Opportunity.workspace_id == workspace_id)
        if stage is not None:
            query = query.filter(Opportunity.stage == stage)
        if assigned_to_id is not None:
            query = query.filter(Opportunity.assigned_to_id == assigned_to_id)
        return query.order_by(Opportunity.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, opportunity_id: str, workspace_id: str) -> Optional[Opportunity]:
        return db.query(Opportunity).filter(
            Opportunity.id == opportunity_id,
            Opportunity.workspace_id == workspace_id
        ).first()

    @staticmethod
    def create(
        db: Session,
        workspace_id: str,
        title: str,
        value: float = 0.0,
        currency: str = "INR",
        stage: PipelineStage = PipelineStage.NEW_LEAD,
        contact_id: Optional[str] = None,
        company_id: Optional[str] = None,
        assigned_to_id: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Opportunity:
        opportunity = Opportunity(
            workspace_id=workspace_id,
            title=title.strip(),
            value=value,
            currency=currency,
            stage=stage.value if isinstance(stage, PipelineStage) else str(stage),
            contact_id=contact_id,
            company_id=company_id,
            assigned_to_id=assigned_to_id,
            custom_fields=custom_fields or {}
        )
        db.add(opportunity)
        db.commit()
        db.refresh(opportunity)
        return opportunity

    @staticmethod
    def update_stage(db: Session, opportunity: Opportunity, stage: PipelineStage) -> Opportunity:
        opportunity.stage = stage.value if isinstance(stage, PipelineStage) else str(stage)
        db.commit()
        db.refresh(opportunity)
        return opportunity

    @staticmethod
    def update(
        db: Session,
        opportunity: Opportunity,
        title: Optional[str] = None,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        stage: Optional[PipelineStage] = None,
        contact_id: Optional[str] = None,
        company_id: Optional[str] = None,
        assigned_to_id: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        stripe_payment_status: Optional[str] = None,
        stripe_session_id: Optional[str] = None
    ) -> Opportunity:
        if title is not None:
            opportunity.title = title.strip()
        if value is not None:
            opportunity.value = value
        if currency is not None:
            opportunity.currency = currency
        if stage is not None:
            opportunity.stage = stage.value if isinstance(stage, PipelineStage) else str(stage)
        if contact_id is not None:
            opportunity.contact_id = contact_id
        if company_id is not None:
            opportunity.company_id = company_id
        if assigned_to_id is not None:
            opportunity.assigned_to_id = assigned_to_id
        if stripe_payment_status is not None:
            opportunity.stripe_payment_status = stripe_payment_status
        if stripe_session_id is not None:
            opportunity.stripe_session_id = stripe_session_id
        if custom_fields is not None:
            updated_fields = dict(opportunity.custom_fields or {})
            updated_fields.update(custom_fields)
            opportunity.custom_fields = updated_fields
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(opportunity, "custom_fields")

        db.commit()
        db.refresh(opportunity)
        return opportunity

    @staticmethod
    def delete(db: Session, opportunity: Opportunity) -> None:
        db.delete(opportunity)
        db.commit()

opportunity_repo = OpportunityRepository()

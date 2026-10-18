from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.lead import Lead, LeadStatus, LeadSource

class LeadRepository:
    @staticmethod
    def get_by_id(db: Session, lead_id: str, workspace_id: Optional[str] = None) -> Optional[Lead]:
        query = db.query(Lead).filter(Lead.id == lead_id)
        if workspace_id is not None:
            query = query.filter(Lead.workspace_id == workspace_id)
        return query.first()

    @staticmethod
    def list_by_workspace(
        db: Session,
        workspace_id: str,
        status: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> List[Lead]:
        query = db.query(Lead).filter(Lead.workspace_id == workspace_id)
        if status is not None:
            query = query.filter(Lead.status == status)
        if owner_id is not None:
            query = query.filter(Lead.owner_id == owner_id)
        return query.order_by(Lead.created_at.desc()).all()

    @staticmethod
    def list_recovery_queue(db: Session, workspace_id: str) -> List[Lead]:
        return db.query(Lead).filter(
            Lead.workspace_id == workspace_id,
            Lead.status == LeadStatus.RECOVERY_QUEUE.value
        ).order_by(Lead.updated_at.desc()).all()

    @staticmethod
    def count_open_leads_for_user(db: Session, workspace_id: str, user_id: str) -> int:
        return db.query(Lead).filter(
            Lead.workspace_id == workspace_id,
            Lead.owner_id == user_id,
            Lead.status.in_([
                LeadStatus.PENDING_ACKNOWLEDGEMENT.value,
                LeadStatus.ACKNOWLEDGED.value
            ])
        ).count()

    @staticmethod
    def create(
        db: Session,
        workspace_id: str,
        title: str,
        contact_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        source: LeadSource = LeadSource.MANUAL,
        status: LeadStatus = LeadStatus.UNASSIGNED,
        escalation_level: int = 0,
        assigned_at: Optional[datetime] = None,
        acknowledgement_deadline: Optional[datetime] = None,
        notes: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Lead:
        lead = Lead(
            workspace_id=workspace_id,
            title=title.strip(),
            contact_id=contact_id,
            owner_id=owner_id,
            source=source.value if isinstance(source, LeadSource) else str(source),
            status=status.value if isinstance(status, LeadStatus) else str(status),
            escalation_level=escalation_level,
            assigned_at=assigned_at,
            acknowledgement_deadline=acknowledgement_deadline,
            notes=notes,
            custom_fields=custom_fields or {}
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def acknowledge(db: Session, lead: Lead) -> Lead:
        now = datetime.now(timezone.utc)
        lead.status = LeadStatus.ACKNOWLEDGED.value
        lead.acknowledged_at = now
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def atomic_escalate(
        db: Session,
        lead_id: str,
        expected_level: int,
        new_level: int,
        new_owner_id: Optional[str],
        new_status: LeadStatus,
        new_assigned_at: Optional[datetime],
        new_deadline: Optional[datetime],
        is_recovered: bool = False
    ) -> bool:
        """
        ATOMIC ESCALATION:
        Uses an atomic conditional UPDATE so two timers firing together CANNOT escalate twice.
        Returns True if row was updated, False if another process already handled or acknowledged it.
        """
        now = datetime.now(timezone.utc)
        rows_updated = db.query(Lead).filter(
            Lead.id == lead_id,
            Lead.escalation_level == expected_level,
            Lead.status == LeadStatus.PENDING_ACKNOWLEDGEMENT.value
        ).update(
            {
                Lead.owner_id: new_owner_id,
                Lead.escalation_level: new_level,
                Lead.status: new_status.value if isinstance(new_status, LeadStatus) else str(new_status),
                Lead.assigned_at: new_assigned_at,
                Lead.acknowledgement_deadline: new_deadline,
                Lead.is_recovered: is_recovered,
                Lead.updated_at: now
            },
            synchronize_session="fetch"
        )
        db.commit()
        return rows_updated > 0

    @staticmethod
    def atomic_reassign(
        db: Session,
        lead_id: str,
        new_owner_id: str,
        new_status: LeadStatus,
        new_assigned_at: datetime,
        new_deadline: datetime
    ) -> bool:
        now = datetime.now(timezone.utc)
        rows_updated = db.query(Lead).filter(
            Lead.id == lead_id
        ).update(
            {
                Lead.owner_id: new_owner_id,
                Lead.status: new_status.value if isinstance(new_status, LeadStatus) else str(new_status),
                Lead.assigned_at: new_assigned_at,
                Lead.acknowledgement_deadline: new_deadline,
                Lead.escalation_level: 0,
                Lead.is_recovered: True,
                Lead.updated_at: now
            },
            synchronize_session="fetch"
        )
        db.commit()
        return rows_updated > 0

lead_repo = LeadRepository()

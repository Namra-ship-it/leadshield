from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User, UserRole, EmployeeStatus
from app.models.lead import LeadStatus, LeadSource
from app.models.workspace import Workspace
from app.schemas.lead import LeadOut, LeadCreate, PublicLeadSubmit, LeadReassign
from app.data_access.lead_repo import lead_repo
from app.data_access.workspace_repo import workspace_repo
from app.data_access.contact_repo import contact_repo
from app.data_access.user_repo import user_repo
from app.business_rules.lead_engine_rules import lead_engine_rules

router = APIRouter(prefix="/leads", tags=["Leads & Lead Engine"])

@router.post("/public", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def submit_public_lead(payload: PublicLeadSubmit, db: Session = Depends(get_db)):
    """
    PUBLIC INBOUND WEB FORM:
    No auth token required. Accepts inbound leads from customer website/landing page.
    Matches or creates a Contact in the target workspace, then auto-routes the lead
    with an active acknowledgement countdown timer.
    """
    workspace = workspace_repo.get_by_slug(db, payload.workspace_slug)
    if not workspace:
        # Check by id as fallback
        workspace = workspace_repo.get_by_id(db, payload.workspace_slug)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{payload.workspace_slug}' not found."
        )

    # 1. Match or create contact
    contact = None
    if payload.phone:
        contact = contact_repo.get_by_phone(db, payload.phone, workspace.id)
    if not contact:
        contact = contact_repo.create(
            db=db,
            workspace_id=workspace.id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone
        )

    # 2. Auto-route lead via round robin with open-lead cap
    lead = lead_engine_rules.route_new_lead(
        db=db,
        workspace=workspace,
        title=f"Inquiry: {payload.full_name}",
        contact_id=contact.id,
        source=LeadSource.WEB_FORM,
        notes=payload.inquiry,
        custom_fields=payload.custom_fields
    )
    return lead

@router.get("", response_model=List[LeadOut])
def list_workspace_leads(
    status: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all leads in the workspace. Regular users see their leads; Admins see all.
    """
    filter_owner = owner_id
    if current_user.role == UserRole.USER.value and filter_owner is None:
        # Regular reps default to their own leads
        filter_owner = current_user.id

    return lead_repo.list_by_workspace(
        db=db,
        workspace_id=current_user.workspace_id,
        status=status,
        owner_id=filter_owner
    )

@router.get("/recovery-queue", response_model=List[LeadOut])
def get_recovery_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Recovery Queue: Lists all leads that were ignored past all escalation thresholds,
    or arrived when all reps were busy/on leave/capped.
    """
    return lead_repo.list_recovery_queue(db, current_user.workspace_id)

@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_manual_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually create an inbound lead. Auto-routes through round robin or assigns to preferred rep.
    """
    workspace = workspace_repo.get_by_id(db, current_user.workspace_id)
    lead = lead_engine_rules.route_new_lead(
        db=db,
        workspace=workspace,
        title=payload.title,
        contact_id=payload.contact_id,
        source=payload.source,
        notes=payload.notes,
        custom_fields=payload.custom_fields,
        preferred_owner_id=payload.owner_id
    )
    return lead

@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = lead_repo.get_by_id(db, lead_id, current_user.workspace_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead

@router.post("/{lead_id}/acknowledge", response_model=LeadOut)
def acknowledge_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stop the countdown timer and prove accountability!
    The assigned rep acknowledges receipt of the lead.
    """
    return lead_engine_rules.acknowledge_lead(db, lead_id, current_user)

@router.post("/{lead_id}/claim", response_model=LeadOut)
def claim_recovery_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    An available rep or manager manually claims a lead from the recovery queue.
    """
    lead = lead_repo.get_by_id(db, lead_id, current_user.workspace_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    if lead.status != LeadStatus.RECOVERY_QUEUE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead is not in the recovery queue.")

    workspace = workspace_repo.get_by_id(db, current_user.workspace_id)
    now = datetime.now(timezone.utc)
    ack_timeout = workspace.settings.get("acknowledgement_timeout_seconds", 300)
    deadline = now + timedelta(seconds=ack_timeout)

    lead_repo.atomic_reassign(
        db=db,
        lead_id=lead.id,
        new_owner_id=current_user.id,
        new_status=LeadStatus.PENDING_ACKNOWLEDGEMENT,
        new_assigned_at=now,
        new_deadline=deadline
    )
    from app.jobs.scheduler import schedule_lead_escalation
    schedule_lead_escalation(lead.id, deadline)
    db.refresh(lead)
    return lead

@router.post("/{lead_id}/reassign", response_model=LeadOut)
def manually_reassign_lead(
    lead_id: str,
    payload: LeadReassign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin manually reassigns a lead to a specific team member.
    """
    lead = lead_repo.get_by_id(db, lead_id, current_user.workspace_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    target_user = user_repo.get_by_id(db, payload.new_owner_id, current_user.workspace_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target user not found in workspace.")

    workspace = workspace_repo.get_by_id(db, current_user.workspace_id)
    now = datetime.now(timezone.utc)
    ack_timeout = workspace.settings.get("acknowledgement_timeout_seconds", 300)
    deadline = now + timedelta(seconds=ack_timeout)

    lead_repo.atomic_reassign(
        db=db,
        lead_id=lead.id,
        new_owner_id=target_user.id,
        new_status=LeadStatus.PENDING_ACKNOWLEDGEMENT,
        new_assigned_at=now,
        new_deadline=deadline
    )
    from app.jobs.scheduler import schedule_lead_escalation
    schedule_lead_escalation(lead.id, deadline)
    db.refresh(lead)
    return lead

@router.post("/{lead_id}/escalate-now", response_model=LeadOut)
def force_escalate_now(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    DEMO ACCELERATOR:
    Instantly trigger the escalation timer logic without waiting for seconds to elapse!
    """
    lead = lead_repo.get_by_id(db, lead_id, current_user.workspace_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    escalated = lead_engine_rules.escalate_lead_atomically(db, lead.id)
    if not escalated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead could not be escalated (may already be acknowledged or closed)."
        )
    db.refresh(lead)
    return lead

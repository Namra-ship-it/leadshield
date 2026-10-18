import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.lead import Lead, LeadStatus, LeadSource
from app.models.user import User, UserRole, EmployeeStatus
from app.models.workspace import Workspace
from app.data_access.lead_repo import lead_repo
from app.data_access.user_repo import user_repo
from app.data_access.workspace_repo import workspace_repo
from app.data_access.contact_repo import contact_repo
from app.jobs.scheduler import schedule_lead_escalation, cancel_lead_escalation

logger = logging.getLogger("lead_engine")

class LeadEngineRules:
    @staticmethod
    def find_eligible_rep(
        db: Session,
        workspace: Workspace,
        exclude_user_ids: Optional[List[str]] = None
    ) -> Optional[User]:
        """
        Finds the best eligible representative using round robin:
        - Must be in this workspace
        - Status must be AVAILABLE (never busy, on_leave, or offline)
        - Must be active
        - Must not be in exclude_user_ids
        - Must not exceed max_open_leads_per_rep
        - Order by last_assigned_at ASC (NULLS FIRST) for fair round robin
        """
        exclude_ids = exclude_user_ids or []
        max_open = workspace.settings.get("max_open_leads_per_rep", 5)

        candidates = db.query(User).filter(
            User.workspace_id == workspace.id,
            User.status == EmployeeStatus.AVAILABLE.value,
            User.is_active == True,
            ~User.id.in_(exclude_ids) if exclude_ids else True
        ).all()

        eligible = []
        for cand in candidates:
            open_count = lead_repo.count_open_leads_for_user(db, workspace.id, cand.id)
            if open_count < max_open:
                eligible.append((cand, cand.last_assigned_at or datetime.min))

        if not eligible:
            return None

        # Sort by least recently assigned
        eligible.sort(key=lambda x: x[1])
        return eligible[0][0]

    @staticmethod
    def route_new_lead(
        db: Session,
        workspace: Workspace,
        title: str,
        contact_id: Optional[str] = None,
        source: LeadSource = LeadSource.MANUAL,
        notes: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        preferred_owner_id: Optional[str] = None
    ) -> Lead:
        now = datetime.now(timezone.utc)
        ack_timeout = workspace.settings.get("acknowledgement_timeout_seconds", 300)

        # 1. Determine assigned rep
        assignee = None
        if preferred_owner_id:
            target = user_repo.get_by_id(db, preferred_owner_id, workspace.id)
            if target and target.status == EmployeeStatus.AVAILABLE.value:
                assignee = target

        if not assignee:
            assignee = LeadEngineRules.find_eligible_rep(db, workspace)

        if assignee:
            # Assign with active countdown timer
            deadline = now + timedelta(seconds=ack_timeout)
            lead = lead_repo.create(
                db=db,
                workspace_id=workspace.id,
                title=title,
                contact_id=contact_id,
                owner_id=assignee.id,
                source=source,
                status=LeadStatus.PENDING_ACKNOWLEDGEMENT,
                escalation_level=0,
                assigned_at=now,
                acknowledgement_deadline=deadline,
                notes=notes,
                custom_fields=custom_fields
            )
            assignee.last_assigned_at = now
            db.commit()

            # Schedule database-persisted countdown timer
            schedule_lead_escalation(lead.id, deadline)
            return lead
        else:
            # No rep available -> Send directly to Recovery Queue
            lead = lead_repo.create(
                db=db,
                workspace_id=workspace.id,
                title=title,
                contact_id=contact_id,
                owner_id=None,
                source=source,
                status=LeadStatus.RECOVERY_QUEUE,
                escalation_level=0,
                assigned_at=None,
                acknowledgement_deadline=None,
                notes=notes,
                custom_fields=custom_fields
            )
            return lead

    @staticmethod
    def acknowledge_lead(db: Session, lead_id: str, current_user: User) -> Lead:
        lead = lead_repo.get_by_id(db, lead_id, current_user.workspace_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        # Must be owner, admin, or workspace owner
        if lead.owner_id != current_user.id and current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned owner or an admin can acknowledge this lead."
            )

        if lead.status == LeadStatus.ACKNOWLEDGED.value:
            return lead

        # Cancel timer
        cancel_lead_escalation(lead.id)
        return lead_repo.acknowledge(db, lead)

    @staticmethod
    def escalate_lead_atomically(db: Session, lead_id: str, expected_level: Optional[int] = None) -> bool:
        """
        Core Escalation Engine:
        Atomically escalates an ignored lead on a visible timer.
        - Level 0 (Initial Owner ignored) -> Level 1 (Backup rep)
        - Level 1 (Backup ignored) -> Level 2 (Manager / Owner)
        - Level 2 (Manager ignored or no backup available) -> Level 3 (Recovery Queue)
        """
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead or lead.status != LeadStatus.PENDING_ACKNOWLEDGEMENT.value:
            return False

        if expected_level is not None and lead.escalation_level != expected_level:
            return False

        workspace = workspace_repo.get_by_id(db, lead.workspace_id)
        if not workspace:
            return False

        now = datetime.now(timezone.utc)
        current_level = lead.escalation_level
        old_owner_id = lead.owner_id

        if current_level == 0:
            # Level 0 -> Level 1: Find backup available rep
            backup_rep = LeadEngineRules.find_eligible_rep(db, workspace, exclude_user_ids=[old_owner_id])
            if backup_rep:
                backup_timeout = workspace.settings.get("escalation_backup_timeout_seconds", 300)
                new_deadline = now + timedelta(seconds=backup_timeout)
                
                success = lead_repo.atomic_escalate(
                    db=db,
                    lead_id=lead.id,
                    expected_level=0,
                    new_level=1,
                    new_owner_id=backup_rep.id,
                    new_status=LeadStatus.PENDING_ACKNOWLEDGEMENT,
                    new_assigned_at=now,
                    new_deadline=new_deadline,
                    is_recovered=False
                )
                if success:
                    backup_rep.last_assigned_at = now
                    db.commit()
                    from app.adapters.base import log_sync_call
                    log_sync_call(
                        provider_type="notify",
                        provider_name="escalation_engine",
                        direction="internal",
                        action="lead_escalated",
                        status="success",
                        workspace_id=lead.workspace_id,
                        event_id=lead.id,
                        payload_summary={
                            "lead_id": lead.id,
                            "title": lead.title,
                            "from_level": 0,
                            "to_level": 1,
                            "old_owner_id": old_owner_id,
                            "new_owner_id": backup_rep.id
                        },
                        response_summary={"status": "escalated", "level": 1, "is_recovered": False},
                        latency_ms=0,
                        db=db
                    )
                    logger.info(f"Escalated lead {lead.id} from {old_owner_id} to backup rep {backup_rep.id}")
                    return True
                return False
            else:
                # No backup rep available, proceed to manager/owner
                current_level = 1

        if current_level == 1:
            # Level 1 -> Level 2: Escalate to Manager / Owner
            manager = db.query(User).filter(
                User.workspace_id == workspace.id,
                User.role.in_([UserRole.OWNER.value, UserRole.ADMIN.value]),
                User.status == EmployeeStatus.AVAILABLE.value,
                User.id != old_owner_id
            ).first()

            if manager:
                mgr_timeout = workspace.settings.get("escalation_manager_timeout_seconds", 300)
                new_deadline = now + timedelta(seconds=mgr_timeout)

                success = lead_repo.atomic_escalate(
                    db=db,
                    lead_id=lead.id,
                    expected_level=1,
                    new_level=2,
                    new_owner_id=manager.id,
                    new_status=LeadStatus.PENDING_ACKNOWLEDGEMENT,
                    new_assigned_at=now,
                    new_deadline=new_deadline,
                    is_recovered=False
                )
                if success:
                    manager.last_assigned_at = now
                    db.commit()
                    from app.adapters.base import log_sync_call
                    log_sync_call(
                        provider_type="notify",
                        provider_name="escalation_engine",
                        direction="internal",
                        action="lead_escalated",
                        status="success",
                        workspace_id=lead.workspace_id,
                        event_id=lead.id,
                        payload_summary={
                            "lead_id": lead.id,
                            "title": lead.title,
                            "from_level": 1,
                            "to_level": 2,
                            "old_owner_id": old_owner_id,
                            "new_owner_id": manager.id
                        },
                        response_summary={"status": "escalated", "level": 2, "is_recovered": False},
                        latency_ms=0,
                        db=db
                    )
                    logger.info(f"Escalated lead {lead.id} to manager {manager.id}")
                    return True
                return False

        # If Level >= 2 or no reps/managers available -> Send to Recovery Queue
        success = lead_repo.atomic_escalate(
            db=db,
            lead_id=lead.id,
            expected_level=lead.escalation_level,
            new_level=3,
            new_owner_id=None,
            new_status=LeadStatus.RECOVERY_QUEUE,
            new_assigned_at=None,
            new_deadline=None,
            is_recovered=True
        )
        if success:
            from app.adapters.base import log_sync_call
            log_sync_call(
                provider_type="notify",
                provider_name="escalation_engine",
                direction="internal",
                action="lead_escalated",
                status="success",
                workspace_id=lead.workspace_id,
                event_id=lead.id,
                payload_summary={
                    "lead_id": lead.id,
                    "title": lead.title,
                    "from_level": current_level,
                    "to_level": 3,
                    "old_owner_id": old_owner_id,
                    "new_owner_id": None
                },
                response_summary={"status": "recovery_queue", "level": 3, "is_recovered": True},
                latency_ms=0,
                db=db
            )
            logger.info(f"Lead {lead.id} moved to Recovery Queue")
            return True

        return False

    @staticmethod
    def handle_user_status_change(db: Session, user: User, new_status: EmployeeStatus) -> int:
        """
        When someone goes On leave, automatically reassign all unacknowledged leads
        to available team members so leads never sit unattended.
        """
        reassigned_count = 0
        if new_status == EmployeeStatus.ON_LEAVE:
            unacked_leads = db.query(Lead).filter(
                Lead.owner_id == user.id,
                Lead.status == LeadStatus.PENDING_ACKNOWLEDGEMENT.value
            ).all()

            workspace = workspace_repo.get_by_id(db, user.workspace_id)
            for lead in unacked_leads:
                cancel_lead_escalation(lead.id)
                next_rep = LeadEngineRules.find_eligible_rep(db, workspace, exclude_user_ids=[user.id])
                now = datetime.now(timezone.utc)
                if next_rep:
                    ack_timeout = workspace.settings.get("acknowledgement_timeout_seconds", 300)
                    deadline = now + timedelta(seconds=ack_timeout)
                    lead_repo.atomic_reassign(
                        db=db,
                        lead_id=lead.id,
                        new_owner_id=next_rep.id,
                        new_status=LeadStatus.PENDING_ACKNOWLEDGEMENT,
                        new_assigned_at=now,
                        new_deadline=deadline
                    )
                    next_rep.last_assigned_at = now
                    schedule_lead_escalation(lead.id, deadline)
                else:
                    # Move to recovery queue
                    lead_repo.atomic_escalate(
                        db=db,
                        lead_id=lead.id,
                        expected_level=lead.escalation_level,
                        new_level=lead.escalation_level,
                        new_owner_id=None,
                        new_status=LeadStatus.RECOVERY_QUEUE,
                        new_assigned_at=None,
                        new_deadline=None,
                        is_recovered=True
                    )
                reassigned_count += 1
            db.commit()
        return reassigned_count

lead_engine_rules = LeadEngineRules()

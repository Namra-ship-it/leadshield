import logging
from datetime import datetime, timezone
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.lead import Lead, LeadStatus

logger = logging.getLogger("lead_scheduler")

# Background scheduler with safety nets: misfire_grace_time and coalesce
scheduler: Optional[BackgroundScheduler] = None

def sweep_overdue_leads(db: Optional[Session] = None):
    """
    Sweeper that runs on startup and every 5 seconds.
    Finds leads whose acknowledgement deadline has expired,
    and escalates overdue leads exactly once.
    Uses SELECT ... FOR UPDATE SKIP LOCKED on PostgreSQL or an atomic conditional
    UPDATE on SQLite/MySQL, records the audit entry, and survives restarts.
    """
    close_db = False
    if db is None:
        from app.core.database import get_current_db_session
        db = get_current_db_session()
        if db is None:
            db = SessionLocal()
            close_db = True

    try:
        now_aware = datetime.now(timezone.utc)
        now_naive = now_aware.replace(tzinfo=None)

        query = db.query(Lead).filter(
            Lead.status == LeadStatus.PENDING_ACKNOWLEDGEMENT.value,
            Lead.acknowledgement_deadline.isnot(None),
            or_(
                Lead.acknowledgement_deadline <= now_aware,
                Lead.acknowledgement_deadline <= now_naive
            )
        )

        # Concurrency safety: SKIP LOCKED if database is PostgreSQL
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)

        overdue_leads = query.all()
        if overdue_leads:
            logger.info(f"[SWEEPER] Found {len(overdue_leads)} overdue lead(s). Processing escalations...")

        for lead in overdue_leads:
            from app.business_rules.lead_engine_rules import lead_engine_rules
            # escalate_lead_atomically uses an atomic conditional UPDATE matching expected_level,
            # ensuring overdue leads escalate exactly once even under concurrent execution.
            lead_engine_rules.escalate_lead_atomically(db, lead.id, expected_level=lead.escalation_level)
    except Exception as e:
        logger.error(f"Error in sweep_overdue_leads: {e}", exc_info=True)
    finally:
        if close_db:
            db.close()

def schedule_lead_escalation(lead_id: str, deadline: Optional[datetime] = None, expected_level: int = 0):
    """
    Replaced one-shot APScheduler jobs with DB-backed deadline on each lead.
    The deadline is persisted in lead.acknowledgement_deadline, and the sweeper
    runs every 5 seconds and on startup. Retained for API backwards compatibility.
    """
    pass

def cancel_lead_escalation(lead_id: str):
    """
    When a lead is acknowledged or reassigned, its status changes away from
    PENDING_ACKNOWLEDGEMENT, so the sweeper will naturally skip it.
    Retained for API backwards compatibility.
    """
    pass

def start_scheduler():
    """
    Starts the sweeper scheduler on startup and registers the 5-second interval job.
    Runs an immediate sweep on startup to catch any leads that became overdue while offline.
    """
    global scheduler
    if scheduler is None or not scheduler.running:
        scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60}
        )
        scheduler.start()
        logger.info("Escalation sweeper scheduler started.")

    scheduler.add_job(
        sweep_overdue_leads,
        "interval",
        seconds=5,
        id="sweeper_lead_escalations",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,
        next_run_time=datetime.now(timezone.utc)
    )

    # Immediate startup sweep to catch any leads past deadline during downtime/restarts
    try:
        sweep_overdue_leads()
    except Exception as e:
        logger.error(f"Error running initial startup sweeper: {e}")

def shutdown_scheduler():
    global scheduler
    if scheduler is not None:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Escalation sweeper scheduler stopped.")

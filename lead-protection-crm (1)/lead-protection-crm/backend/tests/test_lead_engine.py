import pytest
from datetime import datetime, timezone, timedelta
from app.models.lead import LeadStatus, Lead
from app.models.user import EmployeeStatus
from app.models.integration import SyncHistory
from app.business_rules.lead_engine_rules import lead_engine_rules
from app.jobs.scheduler import shutdown_scheduler, start_scheduler, sweep_overdue_leads

def test_public_web_form_and_round_robin_routing(client, db_session):
    """
    Test inbound lead capture from public web form, contact matching,
    and automatic round robin routing with countdown timer.
    """
    # 1. Setup Workspace with Owner (Priya)
    res_signup = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Skyline Properties",
        "full_name": "Priya Sharma",
        "email": "priya@skyline.com",
        "password": "Password123!"
    })
    ws_slug = res_signup.json()["workspace"]["slug"]
    owner_id = res_signup.json()["user"]["id"]

    # 2. Public web form submission
    res_public = client.post("/api/v1/leads/public", json={
        "workspace_slug": ws_slug,
        "full_name": "Arjun Kapoor",
        "email": "arjun@gmail.com",
        "phone": "+919811223344",
        "inquiry": "Interested in 4BHK sea facing flat in Worli."
    })
    assert res_public.status_code == 201, res_public.text
    lead = res_public.json()

    assert lead["status"] == "pending_acknowledgement"
    assert lead["owner_id"] == owner_id
    assert lead["escalation_level"] == 0
    assert lead["acknowledgement_deadline"] is not None
    assert lead["contact_id"] is not None

    # Verify contact was created
    contact_id = lead["contact_id"]
    contact_res = client.get(f"/api/v1/contacts/{contact_id}", headers={
        "Authorization": f"Bearer {res_signup.json()['access_token']}"
    })
    assert contact_res.status_code == 200
    assert contact_res.json()["phone"] == "+919811223344"

def test_acknowledgement_stops_countdown(client):
    """
    Assigned rep acknowledges lead -> stops timer, status becomes acknowledged.
    """
    res_signup = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Solar India",
        "full_name": "Priya Rep",
        "email": "priya@solar.com",
        "password": "Password123!"
    })
    token = res_signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws_slug = res_signup.json()["workspace"]["slug"]

    # Inbound lead
    lead_res = client.post("/api/v1/leads/public", json={
        "workspace_slug": ws_slug,
        "full_name": "Manish Malhotra",
        "email": "manish@example.com",
        "phone": "+919988776655",
        "inquiry": "Looking for 10KW solar plant"
    })
    lead_id = lead_res.json()["id"]

    # Acknowledge lead
    ack_res = client.post(f"/api/v1/leads/{lead_id}/acknowledge", headers=headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "acknowledged"
    assert ack_res.json()["acknowledged_at"] is not None

def test_escalation_chain_when_ignored(client, db_session):
    """
    Test escalation chain:
    Level 0 (Priya ignores) -> Level 1 (Rahul backup) -> Level 2 (Manager) -> Recovery Queue.
    """
    # 1. Owner (Priya)
    res_owner = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Prime Clinic",
        "full_name": "Dr. Priya (Owner)",
        "email": "priya@clinic.com",
        "password": "Password123!"
    })
    owner_token = res_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    ws_id = res_owner.json()["workspace"]["id"]
    ws_slug = res_owner.json()["workspace"]["slug"]

    # 2. Add Rep Rahul
    res_rahul = client.post("/api/v1/users", headers=owner_headers, json={
        "email": "rahul@clinic.com",
        "full_name": "Rahul Backup",
        "password": "Password123!",
        "role": "user"
    })
    rahul_id = res_rahul.json()["id"]

    # 3. Add Manager Karan
    res_karan = client.post("/api/v1/users", headers=owner_headers, json={
        "email": "karan@clinic.com",
        "full_name": "Karan Manager",
        "password": "Password123!",
        "role": "admin"
    })
    karan_id = res_karan.json()["id"]

    # Inbound lead created
    lead_res = client.post("/api/v1/leads/public", json={
        "workspace_slug": ws_slug,
        "full_name": "Patient Sneha",
        "phone": "+919000011111",
        "inquiry": "Need appointment for dental surgery"
    })
    lead_id = lead_res.json()["id"]
    first_owner = lead_res.json()["owner_id"]

    # ESCALATION 1: Trigger escalation from first owner
    esc1 = lead_engine_rules.escalate_lead_atomically(db_session, lead_id)
    assert esc1 is True

    lead_1 = client.get(f"/api/v1/leads/{lead_id}", headers=owner_headers).json()
    assert lead_1["escalation_level"] == 1
    assert lead_1["owner_id"] != first_owner
    assert lead_1["status"] == "pending_acknowledgement"

    # ESCALATION 2: Trigger escalation from backup rep
    esc2 = lead_engine_rules.escalate_lead_atomically(db_session, lead_id)
    assert esc2 is True

    lead_2 = client.get(f"/api/v1/leads/{lead_id}", headers=owner_headers).json()
    assert lead_2["escalation_level"] == 2
    assert lead_2["status"] == "pending_acknowledgement"

    # ESCALATION 3: Final escalation -> Recovery Queue
    esc3 = lead_engine_rules.escalate_lead_atomically(db_session, lead_id)
    assert esc3 is True

    lead_3 = client.get(f"/api/v1/leads/{lead_id}", headers=owner_headers).json()
    assert lead_3["status"] == "recovery_queue"
    assert lead_3["owner_id"] is None
    assert lead_3["is_recovered"] is True

def test_atomic_double_timer_cannot_escalate_twice(client, db_session):
    """
    CRITICAL EXIT CHECK:
    Two timers firing together must NOT escalate it twice (atomic update guarantee).
    """
    res_owner = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Concurrency Real Estate",
        "full_name": "Priya",
        "email": "priya@concurrency.com",
        "password": "Password123!"
    })
    owner_token = res_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    ws_slug = res_owner.json()["workspace"]["slug"]

    # Add second rep
    client.post("/api/v1/users", headers=owner_headers, json={
        "email": "rahul@concurrency.com",
        "full_name": "Rahul",
        "password": "Password123!",
        "role": "user"
    })

    # Create lead
    lead = client.post("/api/v1/leads/public", json={
        "workspace_slug": ws_slug,
        "full_name": "Fast Customer",
        "phone": "+919876500000",
        "inquiry": "Urgent booking"
    }).json()

    # SIMULATE 2 TIMERS FIRING CONCURRENTLY ON THE EXACT SAME LEAD
    # Both timers were set for Level 0 and try to transition from Level 0
    result1 = lead_engine_rules.escalate_lead_atomically(db_session, lead["id"], expected_level=0)
    result2 = lead_engine_rules.escalate_lead_atomically(db_session, lead["id"], expected_level=0)

    # First succeeds, second must be blocked and return False!
    assert result1 is True
    assert result2 is False

    # Lead must be at Level 1, NOT skipped to Level 2
    final_lead = client.get(f"/api/v1/leads/{lead['id']}", headers=owner_headers).json()
    assert final_lead["escalation_level"] == 1

def test_reassign_when_user_goes_on_leave(client):
    """
    When an employee status changes to On leave, their unacknowledged leads
    are immediately reassigned to available team members with fresh timers.
    """
    res_owner = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Leave Testing Agency",
        "full_name": "Owner Priya",
        "email": "priya@leave.com",
        "password": "Password123!"
    })
    token = res_owner.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws_slug = res_owner.json()["workspace"]["slug"]

    # Create Rep Rahul
    res_rahul = client.post("/api/v1/users", headers=headers, json={
        "email": "rahul@leave.com",
        "full_name": "Rahul Rep",
        "password": "Password123!",
        "role": "user"
    })
    rahul_id = res_rahul.json()["id"]

    # Create Rep Sneha
    res_sneha = client.post("/api/v1/users", headers=headers, json={
        "email": "sneha@leave.com",
        "full_name": "Sneha Rep",
        "password": "Password123!",
        "role": "user"
    })
    sneha_id = res_sneha.json()["id"]

    # Create lead assigned to Rahul
    lead = client.post("/api/v1/leads", headers=headers, json={
        "title": "Lead for Rahul",
        "owner_id": rahul_id
    }).json()
    assert lead["owner_id"] == rahul_id
    assert lead["status"] == "pending_acknowledgement"

    # Rahul goes on leave!
    res_leave = client.patch(f"/api/v1/users/{rahul_id}/status", headers=headers, json={
        "status": "on_leave"
    })
    assert res_leave.status_code == 200

    # Verify lead was immediately reassigned away from Rahul
    updated_lead = client.get(f"/api/v1/leads/{lead['id']}", headers=headers).json()
    assert updated_lead["owner_id"] != rahul_id
    assert updated_lead["owner_id"] in [sneha_id, res_owner.json()["user"]["id"]]
    assert updated_lead["status"] == "pending_acknowledgement"

def test_recovery_queue_listing_and_claiming(client):
    """
    Test recovery queue page and claiming a recovered lead.
    """
    res_owner = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Recovery Agency",
        "full_name": "Priya",
        "email": "priya@recovery.com",
        "password": "Password123!"
    })
    token = res_owner.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Put Priya offline so no reps are available
    client.patch(f"/api/v1/users/{res_owner.json()['user']['id']}/status", headers=headers, json={
        "status": "offline"
    })

    # Lead arrives when all reps offline -> goes straight to recovery queue
    lead = client.post("/api/v1/leads/public", json={
        "workspace_slug": res_owner.json()["workspace"]["slug"],
        "full_name": "Orphan Customer",
        "inquiry": "Need urgent contact"
    }).json()

    assert lead["status"] == "recovery_queue"
    assert lead["owner_id"] is None

    # Check recovery queue endpoint
    q_res = client.get("/api/v1/leads/recovery-queue", headers=headers)
    assert q_res.status_code == 200
    queue = q_res.json()
    assert len(queue) == 1
    assert queue[0]["id"] == lead["id"]

    # Rep comes online and claims the lead
    client.patch(f"/api/v1/users/{res_owner.json()['user']['id']}/status", headers=headers, json={
        "status": "available"
    })
    claim_res = client.post(f"/api/v1/leads/{lead['id']}/claim", headers=headers)
    assert claim_res.status_code == 200
    assert claim_res.json()["owner_id"] == res_owner.json()["user"]["id"]
    assert claim_res.json()["status"] == "pending_acknowledgement"

def test_sweeper_escalates_overdue_lead_after_restart(client, db_session):
    """
    Test 1: Escalation timers sweeper:
    Create a lead, stop the server past the deadline, restart, and assert one escalation.
    Asserts exact one-time escalation, audit entry creation, and restart resilience.
    """
    # 1. Setup workspace with Owner (Dr. Priya) and Backup rep (Rahul)
    res_owner = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Sweeper Clinic",
        "full_name": "Dr. Priya (Owner)",
        "email": "priya@sweeperclinic.com",
        "password": "Password123!"
    })
    assert res_owner.status_code == 201
    owner_token = res_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    ws_slug = res_owner.json()["workspace"]["slug"]
    owner_id = res_owner.json()["user"]["id"]

    # Add backup rep
    res_rep = client.post("/api/v1/users", headers=owner_headers, json={
        "email": "rahul@sweeperclinic.com",
        "full_name": "Rahul Backup",
        "password": "Password123!",
        "role": "user"
    })
    assert res_rep.status_code == 201
    rep_id = res_rep.json()["id"]

    # 2. Inbound lead created with countdown timer
    lead_res = client.post("/api/v1/leads/public", json={
        "workspace_slug": ws_slug,
        "full_name": "Emergency Patient",
        "phone": "+919876543210",
        "inquiry": "Need urgent doctor consultation"
    })
    assert lead_res.status_code == 201
    lead_data = lead_res.json()
    lead_id = lead_data["id"]
    first_owner = lead_data["owner_id"]
    assert lead_data["escalation_level"] == 0
    assert lead_data["status"] == "pending_acknowledgement"
    assert lead_data["acknowledgement_deadline"] is not None

    # 3. Stop the server
    shutdown_scheduler()

    # Past the deadline: advance the lead's acknowledgement_deadline to the past
    past_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    lead_obj = db_session.query(Lead).filter(Lead.id == lead_id).first()
    lead_obj.acknowledgement_deadline = past_time
    db_session.commit()

    # 4. Restart the server (start_scheduler runs on startup and triggers immediate sweep)
    start_scheduler()

    # 5. Assert ONE escalation occurred
    db_session.refresh(lead_obj)
    assert lead_obj.escalation_level == 1
    assert lead_obj.owner_id != first_owner
    assert lead_obj.owner_id == rep_id
    assert lead_obj.status == "pending_acknowledgement"

    # Verify audit entry was recorded in SyncHistory
    audit_entries = db_session.query(SyncHistory).filter(
        SyncHistory.event_id == lead_id,
        SyncHistory.action == "lead_escalated"
    ).all()
    assert len(audit_entries) == 1
    assert audit_entries[0].status == "success"
    assert audit_entries[0].payload_summary["from_level"] == 0
    assert audit_entries[0].payload_summary["to_level"] == 1

    # Safety check: running the sweeper again does NOT escalate it twice
    sweep_overdue_leads(db_session)
    db_session.refresh(lead_obj)
    assert lead_obj.escalation_level == 1

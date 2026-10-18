import pytest

def test_crm_core_lifecycle_and_stage_moves(client):
    # 1. Signup Owner (Priya)
    res_a = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Apex Realty",
        "full_name": "Priya Sharma",
        "email": "priya@apex.com",
        "password": "Password123!"
    })
    token = res_a.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Company
    res_comp = client.post("/api/v1/companies", headers=headers, json={
        "name": "Tata Housing",
        "domain": "tatahousing.com"
    })
    assert res_comp.status_code == 201
    company_id = res_comp.json()["id"]

    # 3. Create Contact
    res_contact = client.post("/api/v1/contacts", headers=headers, json={
        "full_name": "Vikram Sethi",
        "email": "vikram@example.com",
        "phone": "+919876543210",
        "company_id": company_id
    })
    assert res_contact.status_code == 201
    contact_id = res_contact.json()["id"]

    # 4. Create Opportunity
    res_opp = client.post("/api/v1/opportunities", headers=headers, json={
        "title": "3BHK Luxury Penthouse",
        "value": 15000000.0,
        "currency": "INR",
        "stage": "new_lead",
        "contact_id": contact_id,
        "company_id": company_id
    })
    assert res_opp.status_code == 201
    opp_data = res_opp.json()
    opp_id = opp_data["id"]
    assert opp_data["stage"] == "new_lead"
    assert opp_data["value"] == 15000000.0

    # 5. Pipeline Stage Move (Stage drag / move)
    res_stage = client.patch(f"/api/v1/opportunities/{opp_id}/stage", headers=headers, json={
        "stage": "proposal_sent"
    })
    assert res_stage.status_code == 200
    assert res_stage.json()["stage"] == "proposal_sent"

    # 6. List opportunities by stage
    res_list = client.get("/api/v1/opportunities?stage=proposal_sent", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1
    assert res_list.json()[0]["id"] == opp_id

def test_admin_custom_fields_and_user_restriction(client):
    """
    Test requirement: two custom fields an Admin can add from the UI.
    Also verify regular User cannot create custom fields.
    """
    # 1. Owner registers
    res_owner = client.post("/api/v1/auth/signup", json={
        "workspace_name": "SolarTech Labs",
        "full_name": "Dr. Sameer",
        "email": "sameer@solartech.com",
        "password": "Password123!"
    })
    owner_token = res_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Owner creates Admin (Maya)
    res_admin = client.post("/api/v1/users", headers=owner_headers, json={
        "email": "maya@solartech.com",
        "full_name": "Maya Admin",
        "password": "Password123!",
        "role": "admin"
    })
    assert res_admin.status_code == 201

    # 3. Owner creates User (Raj)
    res_user = client.post("/api/v1/users", headers=owner_headers, json={
        "email": "raj@solartech.com",
        "full_name": "Raj Rep",
        "password": "Password123!",
        "role": "user"
    })
    assert res_user.status_code == 201

    # Login as Admin
    login_admin = client.post("/api/v1/auth/login", json={
        "email": "maya@solartech.com",
        "password": "Password123!"
    })
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Login as User
    login_user = client.post("/api/v1/auth/login", json={
        "email": "raj@solartech.com",
        "password": "Password123!"
    })
    user_token = login_user.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 4. User attempts to add a custom field -> MUST FAIL with 403 Forbidden
    res_unauth = client.post("/api/v1/custom-fields", headers=user_headers, json={
        "entity_type": "contact",
        "label": "Roof Size SqFt",
        "field_type": "number"
    })
    assert res_unauth.status_code == 403

    # 5. Admin adds Custom Field 1: "Property Type" for contacts
    field1 = client.post("/api/v1/custom-fields", headers=admin_headers, json={
        "entity_type": "contact",
        "label": "Property Type",
        "field_type": "select",
        "options": ["Residential", "Commercial", "Industrial"]
    })
    assert field1.status_code == 201
    f1_key = field1.json()["field_key"]

    # 6. Admin adds Custom Field 2: "Target KW Capacity" for opportunities
    field2 = client.post("/api/v1/custom-fields", headers=admin_headers, json={
        "entity_type": "opportunity",
        "label": "Target KW Capacity",
        "field_type": "number"
    })
    assert field2.status_code == 201
    f2_key = field2.json()["field_key"]

    # 7. Create contact with custom field populated
    contact_res = client.post("/api/v1/contacts", headers=admin_headers, json={
        "full_name": "Sunil Grover",
        "email": "sunil@example.com",
        "custom_fields": {
            f1_key: "Commercial"
        }
    })
    assert contact_res.status_code == 201
    assert contact_res.json()["custom_fields"][f1_key] == "Commercial"

    # 8. Create opportunity with custom field populated
    opp_res = client.post("/api/v1/opportunities", headers=admin_headers, json={
        "title": "50KW Rooftop Solar Installation",
        "value": 2500000.0,
        "contact_id": contact_res.json()["id"],
        "custom_fields": {
            f2_key: 50
        }
    })
    assert opp_res.status_code == 201
    assert opp_res.json()["custom_fields"][f2_key] == 50

def test_crm_workspace_isolation(client):
    """
    CRITICAL EXIT CHECK:
    Workspace A cannot read or modify Workspace B's contacts, companies, or opportunities.
    """
    # Workspace A
    res_a = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Agency A",
        "full_name": "Alice A",
        "email": "alice@a.com",
        "password": "Password123!"
    })
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Workspace B
    res_b = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Agency B",
        "full_name": "Bob B",
        "email": "bob@b.com",
        "password": "Password123!"
    })
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Workspace A creates Contact & Opportunity
    contact_a = client.post("/api/v1/contacts", headers=headers_a, json={
        "full_name": "Secret Client A"
    }).json()
    opp_a = client.post("/api/v1/opportunities", headers=headers_a, json={
        "title": "Confidential Deal A",
        "contact_id": contact_a["id"]
    }).json()

    # Workspace B attempts to get Contact A by ID -> MUST BE 404
    probe_contact = client.get(f"/api/v1/contacts/{contact_a['id']}", headers=headers_b)
    assert probe_contact.status_code == 404

    # Workspace B attempts to get Opportunity A by ID -> MUST BE 404
    probe_opp = client.get(f"/api/v1/opportunities/{opp_a['id']}", headers=headers_b)
    assert probe_opp.status_code == 404

    # Workspace B attempts to link Opportunity B to Contact A -> MUST BE 400 Bad Request
    illegal_link = client.post("/api/v1/opportunities", headers=headers_b, json={
        "title": "Cross Tenant Exploit Deal",
        "contact_id": contact_a["id"]
    })
    assert illegal_link.status_code == 400

    # Workspace B listing contacts -> MUST BE EMPTY
    list_b = client.get("/api/v1/contacts", headers=headers_b)
    assert len(list_b.json()) == 0

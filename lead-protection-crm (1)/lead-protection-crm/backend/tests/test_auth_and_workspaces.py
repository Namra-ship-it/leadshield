from app.models.user import User
from app.models.workspace import Workspace

def test_signup_creates_workspace_and_owner(client, db_session):
    signup_payload = {
        "workspace_name": "Apex Realty",
        "full_name": "Priya Sharma",
        "email": "priya@apexrealty.com",
        "password": "SecurePassword123!"
    }
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "owner"
    assert data["user"]["email"] == "priya@apexrealty.com"
    assert data["workspace"]["name"] == "Apex Realty"
    assert "slug" in data["workspace"]

    # Verify database record & Argon2 password hashing
    db_user = db_session.query(User).filter(User.email == "priya@apexrealty.com").first()
    assert db_user is not None
    assert db_user.role == "owner"
    assert db_user.hashed_password != "SecurePassword123!"
    # Verify Argon2 hash format
    assert db_user.hashed_password.startswith("$argon2")

def test_login_success_and_invalid_credentials(client):
    # 1. Signup user
    signup_payload = {
        "workspace_name": "Solar Pros",
        "full_name": "Amit Patel",
        "email": "amit@solarpros.com",
        "password": "SolarPassword2026!"
    }
    client.post("/api/v1/auth/signup", json=signup_payload)

    # 2. Login with correct credentials
    login_res = client.post("/api/v1/auth/login", json={
        "email": "amit@solarpros.com",
        "password": "SolarPassword2026!"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["user"]["full_name"] == "Amit Patel"

    # 3. Login with wrong password
    bad_res = client.post("/api/v1/auth/login", json={
        "email": "amit@solarpros.com",
        "password": "WrongPassword!"
    })
    assert bad_res.status_code == 401

    # 4. Profile /me check
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["email"] == "amit@solarpros.com"
    assert me_data["workspace"]["name"] == "Solar Pros"

def test_workspace_isolation_between_tenants(client):
    """
    CRITICAL EXIT CHECK:
    Two workspaces cannot see each other's data, even by guessing IDs.
    """
    # Create Workspace A (Priya at Apex Realty)
    res_a = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Apex Realty",
        "full_name": "Priya Sharma",
        "email": "priya@apex.com",
        "password": "Password123!"
    })
    token_a = res_a.json()["access_token"]
    ws_a_id = res_a.json()["workspace"]["id"]
    user_a_id = res_a.json()["user"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Create Workspace B (Rahul at Metro Housing)
    res_b = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Metro Housing",
        "full_name": "Rahul Verma",
        "email": "rahul@metro.com",
        "password": "Password456!"
    })
    token_b = res_b.json()["access_token"]
    ws_b_id = res_b.json()["workspace"]["id"]
    user_b_id = res_b.json()["user"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Priya attempts to view Metro Housing workspace by guessing ws_b_id
    probe_ws = client.get(f"/api/v1/workspaces/{ws_b_id}", headers=headers_a)
    assert probe_ws.status_code in [403, 404], "Workspace isolation failed: User accessed another workspace!"

    # 2. Priya attempts to view Rahul's user profile by guessing user_b_id
    probe_user = client.get(f"/api/v1/users/{user_b_id}", headers=headers_a)
    assert probe_user.status_code in [403, 404], "User isolation failed: User accessed member of another workspace!"

    # 3. Priya lists users - must ONLY see her own workspace users
    list_res = client.get("/api/v1/users", headers=headers_a)
    assert list_res.status_code == 200
    users_list = list_res.json()
    assert len(users_list) == 1
    assert users_list[0]["id"] == user_a_id
    assert users_list[0]["email"] == "priya@apex.com"

    # 4. Rahul attempts to access Workspace A by guessing ws_a_id
    probe_ws_b = client.get(f"/api/v1/workspaces/{ws_a_id}", headers=headers_b)
    assert probe_ws_b.status_code in [403, 404]

def test_rbac_roles_and_permissions(client):
    """
    Test permissions for Owner, Admin, and User roles.
    """
    # 1. Signup Owner (Priya)
    res = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Health Clinic",
        "full_name": "Dr. Priya",
        "email": "drpriya@clinic.com",
        "password": "Password123!"
    })
    owner_token = res.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Owner creates an Admin (Karan)
    res_admin = client.post("/api/v1/users", headers=owner_headers, json={
        "email": "karan@clinic.com",
        "full_name": "Karan Malhotra",
        "password": "KaranPassword123!",
        "role": "admin"
    })
    assert res_admin.status_code == 201
    admin_id = res_admin.json()["id"]

    # 3. Owner creates a regular User (Ananya)
    res_user = client.post("/api/v1/users", headers=owner_headers, json={
        "email": "ananya@clinic.com",
        "full_name": "Ananya Roy",
        "password": "AnanyaPassword123!",
        "role": "user"
    })
    assert res_user.status_code == 201
    user_id = res_user.json()["id"]

    # 4. Login as User (Ananya)
    login_user = client.post("/api/v1/auth/login", json={
        "email": "ananya@clinic.com",
        "password": "AnanyaPassword123!"
    })
    user_token = login_user.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 5. User tries to create another user -> MUST BE 403 Forbidden
    res_unauth_create = client.post("/api/v1/users", headers=user_headers, json={
        "email": "sneha@clinic.com",
        "full_name": "Sneha",
        "password": "Password123!",
        "role": "user"
    })
    assert res_unauth_create.status_code == 403

    # 6. User tries to update workspace configuration -> MUST BE 403 Forbidden
    res_unauth_ws = client.put("/api/v1/workspaces/current", headers=user_headers, json={
        "name": "Hacked Clinic Name"
    })
    assert res_unauth_ws.status_code == 403

    # 7. Login as Admin (Karan)
    login_admin = client.post("/api/v1/auth/login", json={
        "email": "karan@clinic.com",
        "password": "KaranPassword123!"
    })
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 8. Admin can create a regular user
    res_admin_creates = client.post("/api/v1/users", headers=admin_headers, json={
        "email": "rohit@clinic.com",
        "full_name": "Rohit Kumar",
        "password": "Password123!",
        "role": "user"
    })
    assert res_admin_creates.status_code == 201

    # 9. Admin CANNOT promote anyone to Owner -> 403 Forbidden
    res_admin_promotes_owner = client.patch(f"/api/v1/users/{user_id}/role", headers=admin_headers, json={
        "role": "owner"
    })
    assert res_admin_promotes_owner.status_code == 403

    # 10. Owner updates workspace configuration -> Success!
    res_owner_update = client.put("/api/v1/workspaces/current", headers=owner_headers, json={
        "name": "Apollo Prime Clinic",
        "settings": {
            "acknowledgement_timeout_seconds": 20,
            "max_open_leads_per_rep": 3
        }
    })
    assert res_owner_update.status_code == 200
    assert res_owner_update.json()["name"] == "Apollo Prime Clinic"
    assert res_owner_update.json()["settings"]["acknowledgement_timeout_seconds"] == 20

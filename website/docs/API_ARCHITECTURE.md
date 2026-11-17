# TMA-DHI Backend API Architecture Specification
## FastAPI & PostgreSQL RESTful Architecture

> **Stack:** Python 3.11+, FastAPI, SQLAlchemy, Alembic, PostgreSQL, JWT (OAuth2 Password Bearer) with Argon2id.

---

## 1. Authentication & Role-Based Authorization Flow

```
[Client / Frontend]
        │
        ▼ 1. POST /api/v1/auth/login {email, password}
[FastAPI Auth Controller]
        │
        ▼ 2. Verify Argon2id hash against user_accounts table
[PostgreSQL Database]
        │
        ▲ 3. Query Active Approved Membership & Roles
        │
[FastAPI Token Issuer]
        │
        ▼ 4. Return {access_token: JWT, refresh_token: JWT, roles: [...]}
[Client Stores JWT]
```

### Security Dependencies in Python

```python
# Auth Guard Dependency
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserAccount:
    ...

# Active Membership Guard (Rejects unapproved applicants from internal endpoints)
async def get_current_approved_member(user: UserAccount = Depends(get_current_user)) -> Membership:
    if not user.membership or user.membership.status != "approved":
        raise HTTPException(status_code=403, detail="Active approved TMA-DHI membership required.")
    return user.membership

# Permission Guard (Leadership, Curator, Admin)
def require_permission(permission_name: str):
    def dependency(user: UserAccount = Depends(get_current_user)):
        if not user.has_permission(permission_name):
            raise HTTPException(status_code=403, detail=f"Permission '{permission_name}' required.")
        return user
    return dependency
```

---

## 2. API Endpoint Directory (Version 1)

### Domain A: Authentication & Identity (`/api/v1/auth`)
* `POST /api/v1/auth/register`: Public registration (creates `persons` draft and `user_accounts` record).
* `POST /api/v1/auth/login`: Authenticate and issue JWT access token.
* `POST /api/v1/auth/refresh`: Refresh expired access token.
* `GET  /api/v1/auth/me`: Fetch authenticated user profile, active membership status, and assigned roles.

### Domain B: Membership & Governance (`/api/v1/memberships`)
* `POST /api/v1/memberships/apply`: Submit membership application with professional documents & CV.
* `GET  /api/v1/memberships/pending`: List pending applications (Leadership / Admin only).
* `POST /api/v1/memberships/{id}/review`: Approve, reject, or request information on an application.
* `GET  /api/v1/memberships/directory`: Public directory of approved members with skills and publications.

### Domain C: Projects & Innovation (`/api/v1/projects`)
* `GET  /api/v1/projects`: List public or members-only projects with filters (e.g. `focus_area=telephony_ai`).
* `POST /api/v1/projects`: Propose a new project (requires Approved Member status).
* `GET  /api/v1/projects/{slug}`: Project workspace, team roster, linked datasets, and milestone progress.
* `POST /api/v1/projects/{id}/members`: Invite or assign members to a project team.

### Domain D: Digital Health Products (`/api/v1/products`)
* `GET  /api/v1/products`: Browse showcase of developed tools (e.g., Mkri Hakaym 2G Voice AI, EMR tools).
* `POST /api/v1/products`: Register a new digital health solution.
* `PUT  /api/v1/products/{id}/status`: Update deployment status (`idea` ➔ `prototype` ➔ `testing` ➔ `deployed`).

### Domain E: Clinical Datasets & Governance (`/api/v1/datasets`)
* `GET  /api/v1/datasets`: Discover cataloged datasets (open metadata, restricted files).
* `POST /api/v1/datasets`: Submit a new dataset with ethical clearance documentation.
* `POST /api/v1/datasets/{id}/versions`: Upload new version checksum and S3 storage keys.
* `POST /api/v1/datasets/{id}/access-request`: Request access to restricted health data with scientific justification.
* `POST /api/v1/datasets/access-requests/{id}/review`: Curator approval/rejection of access request.

### Domain F: Research & Publications (`/api/v1/publications`)
* `GET  /api/v1/publications`: Search clinical and AI health research publications by author, DOI, or date.
* `POST /api/v1/publications`: Register publication with author order attribution.

### Domain G: Communities of Practice (`/api/v1/communities`)
* `GET  /api/v1/communities`: List Communities of Practice (AI in Health, Telemedicine, Health Systems).
* `POST /api/v1/communities/{id}/join`: Join a community.
* `GET  /api/v1/communities/{id}/discussions`: Threaded discussions and clinical case exchanges.
* `POST /api/v1/communities/{id}/discussions`: Post inquiry or clinical question.
* `POST /api/v1/discussions/{id}/comments`: Post comment or peer review.

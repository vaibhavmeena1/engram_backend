# MCP and Dashboard Authentication with Google Workspace OAuth and Personal Access Tokens

## Decision

Engram should treat the backend as the **single authentication authority** for both the web dashboard and MCP clients.

Google Workspace OAuth/OIDC is used only to prove the user's identity to the backend. After Google login, the backend creates its own internal web session/JWT. MCP does **not** run a separate OAuth callback/device flow for the MVP. Instead, authenticated dashboard users generate **Personal Access Tokens** for MCP from the web UI.

| Client | Backend credential | Transport |
|---|---|---|
| Dashboard/web app | Backend-owned web session/JWT created after Google OAuth | `HttpOnly`, `Secure` cookie |
| MCP / Claude Code | User-owned Personal Access Token generated from dashboard | `Authorization: Bearer <personal-access-token>` |
| Future CLI/automation | User-owned Personal Access Token, or a dedicated OAuth flow later | `Authorization: Bearer <personal-access-token>` |

The backend should not trust or persist Google's ID token as the app session credential. Google proves identity; the backend owns sessions, Personal Access Tokens, RBAC, auditability, and revocation.

```text
                 Google Workspace OAuth/OIDC
                           │
                           ▼
                Engram Backend/Auth
                           │
           ┌───────────────┴────────────────┐
           │                                │
           ▼                                ▼
 Dashboard Web UI                    MCP / Claude Code
 Backend web cookie/JWT              Personal Access Token
           │                                │
           └──── both resolve ActorContext ─────┘
```

This replaces the previous phase-1 shared config API key/secret model. There should be **no shared config-based MCP API key or API secret** in production or local config templates. All MCP keys should be created from the authenticated web dashboard and tied to a real user.

---

## Current State in This Backend

The backend currently has the correct service boundary but the old implementation is still incomplete for the target auth model:

- `services/auth_context_service.py`
  - Should become a small dispatcher for web-cookie and Personal Access Token credentials.
  - It should not own Google OAuth internals or Personal Access Token hashing/storage.
  - It should convert verified credentials into the shared `ActorContext` contract.
- `routers/dependencies.py`
  - Uses `resolve_actor()` for dashboard REST APIs.
- `services/mcp_context_service.py`
  - Uses the same `AuthContextService.resolve_actor_context()` for MCP tools.
- `models/identity.py`
  - Has `Organization`, `User`, `Role`, and `RoleAssignment`.
  - Needs identity, web session, and Personal Access Token models.
- `schemas/enums.py`
  - Should include auth methods for `oauth_web_cookie` and `personal_access_token`.

This is the right architecture: MCP tools, dashboard APIs, RBAC, audit, and memory services depend on `ActorContext`, not raw credentials. The auth migration should preserve that contract.

---

## Target Login and Token Flows

### Dashboard flow

```text
Dashboard
    │
    │  GET /auth/google/login?client_type=web
    ▼
Backend
    │
    │  Redirect to Google Workspace OAuth
    ▼
Google
    │
    │  Redirect back with authorization code
    ▼
Backend /auth/google/callback
    │
    │  Exchange code
    │  Verify Google ID token
    │  Enforce email_verified + @1mg.com
    │  Upsert user + Google identity
    │  Create backend web session/JWT
    │  Set HttpOnly Secure cookie
    ▼
Dashboard authenticated
```

The browser stores only the backend cookie. JavaScript should not read the session token.

### MCP flow with web-generated Personal Access Token

```text
User opens dashboard settings
    │
    │  Login through Google OAuth if needed
    ▼
Dashboard calls backend with web cookie
    │
    │  POST /auth/personal-access-tokens
    ▼
Backend
    │
    │  Creates user-owned PAT
    │  Stores only token hash
    │  Returns raw token once
    ▼
User/plugin stores PAT locally
    │
    │  Claude Code MCP sends Authorization: Bearer <PAT>
    ▼
Backend resolves PAT → user/org/roles → ActorContext
```

This avoids the complexity of MCP OAuth callback/device flows for the MVP and matches how Claude Code MCP config normally passes static headers.

---

## Personal Access Token Naming

Use this naming consistently:

| Name | Usage |
|---|---|
| **Personal Access Token** | User-facing and doc-facing name |
| `personal_access_token` | Auth method / service/model naming |
| `PAT` | Acceptable abbreviation in prose |
| `engpat` | Recommended raw token prefix |

Avoid these names for the new user-owned tokens:

- `API_SECRET`
- `shared API key`
- `phase-1 API key`
- `MCP API secret`

Those names imply the old shared service credential model.

Recommended raw token shape:

```text
engpat_live_<random-url-safe-secret>
```

For local/dev you can use:

```text
engpat_dev_<random-url-safe-secret>
```

The prefix is for quick identification only. Authorization must be based on the hash lookup, not the visible prefix.

---

## Configuration

`ENGRAM_AUTH` should contain Google OAuth/web-session settings and Personal Access Token policy. It should not contain shared MCP `API_KEY` or `API_SECRET` values.

Target config shape:

```json
{
  "ENGRAM_AUTH": {
    "MODE": "google_workspace_oidc",
    "PHASE1_HEADER_ENABLED": false,
    "ALLOWED_EMAIL_DOMAINS": ["1mg.com"],
    "GOOGLE_HOSTED_DOMAIN": "1mg.com",
    "DEFAULT_ORG_SLUG": "tata1mg",
    "ADMIN_EMAILS": [],
    "AUTO_PROVISION_USERS": true,

    "GOOGLE_CLIENT_ID": "",
    "GOOGLE_CLIENT_SECRET": "",
    "GOOGLE_AUTHORIZATION_ENDPOINT": "https://accounts.google.com/o/oauth2/v2/auth",
    "GOOGLE_TOKEN_ENDPOINT": "https://oauth2.googleapis.com/token",
    "GOOGLE_JWKS_URI": "https://www.googleapis.com/oauth2/v3/certs",
    "GOOGLE_REDIRECT_URI": "http://localhost:8000/auth/google/callback",

    "JWT_ISSUER": "engram-backend",
    "JWT_AUDIENCE": "engram-clients",
    "JWT_SIGNING_ALGORITHM": "HS256",
    "JWT_SIGNING_KEY": "",
    "ACCESS_TOKEN_TTL_SECONDS": 86400,
    "WEB_SESSION_TTL_SECONDS": 86400,

    "SESSION_COOKIE_NAME": "engram_session",
    "SESSION_COOKIE_DOMAIN": "",
    "SESSION_COOKIE_SECURE": true,
    "SESSION_COOKIE_HTTP_ONLY": true,
    "SESSION_COOKIE_SAME_SITE": "lax",

    "DASHBOARD_LOGIN_SUCCESS_URL": "http://localhost:5173/",
    "DASHBOARD_LOGIN_FAILURE_URL": "http://localhost:5173/login?error=auth_failed",

    "PERSONAL_ACCESS_TOKENS_ENABLED": true,
    "PERSONAL_ACCESS_TOKEN_PREFIX": "engpat",
    "PERSONAL_ACCESS_TOKEN_DEFAULT_TTL_SECONDS": 7776000,
    "PERSONAL_ACCESS_TOKEN_MAX_TTL_SECONDS": 15552000,
    "PERSONAL_ACCESS_TOKEN_HASH_SECRET": ""
  }
}
```

Notes:

- `GOOGLE_CLIENT_SECRET`, `JWT_SIGNING_KEY`, and `PERSONAL_ACCESS_TOKEN_HASH_SECRET` must come from deployment secrets/Vault in real environments.
- `PERSONAL_ACCESS_TOKEN_HASH_SECRET` is a server-side pepper/HMAC secret used to hash PATs before storage.
- `API_KEY`, `API_SECRET`, `MCP_TOKEN_TTL_SECONDS`, and `LOGIN_CODE_TTL_SECONDS` are no longer part of the target MCP flow.
- If the dashboard and API are cross-site and cookies require `SameSite=None`, add CSRF protection for state-changing dashboard requests.

---

## Google Workspace OAuth Setup

Preferred production setup:

1. Use a Google Cloud project controlled by the 1mg/Tata 1mg Workspace.
2. Configure the OAuth consent screen as **Internal** if available.
3. Create an OAuth Client ID of type **Web application**.
4. Configure backend redirect URI:

```text
https://<backend-domain>/auth/google/callback
```

5. For local development add:

```text
http://localhost:8000/auth/google/callback
```

6. Request only:

```text
openid email profile
```

Backend enforcement is still required even for an Internal Google app:

- Verify ID token audience equals `GOOGLE_CLIENT_ID`.
- Verify issuer is Google.
- Verify expiration/signature through the OIDC library.
- Verify `email_verified = true`.
- Verify normalized email domain is `1mg.com`.
- If present, verify hosted domain (`hd`) is `1mg.com`.
- Store Google `sub` as the stable external identity key.
- Do not use email as the only permanent external identifier.

---

## Database Models

Add persistent identity, web session, and Personal Access Token tables. Keep these in `models/identity.py` unless the file grows too large; if it does, split cleanly under `models/identity/` or another focused auth model module and register it in DB config.

### `engram_user_identities`

```text
id
user_id
provider              -- "google"
provider_subject      -- Google sub
email_at_login
email_verified
hosted_domain
profile               -- safe claims: name, picture, locale
created_at
updated_at

Unique(provider, provider_subject)
```

### `engram_sessions`

For dashboard web sessions:

```text
id
user_id
org_id
client_type           -- "web"
jwt_id_hash           -- hash of web-session jti if using JWT cookies
created_at
last_seen_at
expires_at
revoked_at
revoked_reason
metadata              -- user agent, ip hash, etc.
```

### `engram_personal_access_tokens`

For MCP/CLI access:

```text
id
user_id
org_id
name                  -- "Claude Code on MacBook"
key_prefix            -- visible prefix for display, e.g. "engpat_live_ab12"
token_hash            -- HMAC/SHA hash of the full raw token
client_type           -- "mcp" | "cli" | "automation"
scopes                -- JSON/list, e.g. ["mcp"] for MVP
created_at
last_used_at
expires_at
revoked_at
revoked_reason
metadata              -- plugin version, created user-agent, etc.
```

Rules:

- Store only `token_hash`, never the raw token.
- Show the raw token exactly once during creation.
- `key_prefix` is only for user display/debugging.
- Expiry should be enabled by default.
- Revocation should be possible from the dashboard.

---

## Auth Methods and ActorContext

Auth methods should be:

```text
phase1_header              -- legacy only; do not use for target flow
oauth_web_cookie           -- dashboard web cookie/session
personal_access_token      -- MCP/CLI PAT bearer token
```

Consider extending `ActorContext` with optional fields when implementation starts:

```text
session_id: UUID | None
personal_access_token_id: UUID | None
client_type: str | None
```

Keep the existing core fields stable:

```text
actor_user_id
email
org_id
org_slug
client_name
request_id
auth_method
roles
permissions
```

Every dashboard API and MCP tool should continue receiving a resolved `ActorContext` before reaching memory/RBAC services.

---

## Service and Folder Structure

Keep auth implementation modular. Do not dump OAuth, token hashing, session handling, and router code into `mcp_router.py` or a single large auth file.

Recommended backend structure:

```text
services/auth_context_service.py
- Small dispatcher only.
- Reads web cookie or Authorization bearer header.
- Delegates verification to focused services.
- Converts verified user/org/client into ActorContext.

services/google_oauth_service.py
- Builds Google authorization URL.
- Handles callback token exchange.
- Verifies Google ID token claims.
- Enforces Workspace/domain policy.

services/session_service.py
- Creates dashboard web sessions.
- Verifies active sessions.
- Revokes sessions.
- Updates last_seen_at.

services/token_service.py
- Issues/verifies backend web-session JWTs.
- Hashes JWT jti values if session lineage is stored.
- Does not manage Personal Access Tokens.

services/personal_access_token_service.py
- Generates PATs.
- Hashes PATs using server-side HMAC/pepper.
- Lists/revokes PAT metadata.
- Verifies bearer PATs and resolves owner user/org.

services/user_identity_service.py
- Resolves or creates users after Google login.
- Upserts Google identity rows.
- Updates safe profile metadata.

routers/auth.py
- Google login/callback/logout/me endpoints.
- Should not contain low-level OAuth verification logic.

routers/personal_access_tokens.py
- Dashboard-authenticated PAT create/list/revoke endpoints.
- Should not be mounted under MCP router.

schemas/auth.py
- Auth request/response DTOs.
- PAT create/list response schemas.
```

Clean-code rules:

- One file should have one auth responsibility.
- Routers should validate request/response shape and call services.
- Services should own business logic.
- Models should not generate tokens or parse HTTP headers.
- MCP tools should never parse PATs directly; they should consume `ActorContext` only.

---

## Auth Resolver Behavior

`AuthContextService.resolve_actor_context(request)` should support:

### 1. Web cookie credential

- Read backend session/JWT cookie.
- Verify JWT signature and claims.
- Verify session row exists and is active.
- Resolve user/org/roles.
- Return `ActorContext(auth_method=oauth_web_cookie)`.

### 2. MCP/CLI Personal Access Token credential

- Read `Authorization: Bearer <personal-access-token>`.
- Verify token prefix format enough to route parsing.
- Hash/HMAC the raw token.
- Look up active token record.
- Ensure token is not expired or revoked.
- Resolve owning user/org/roles.
- Update `last_used_at` asynchronously or safely after verification.
- Return `ActorContext(auth_method=personal_access_token)`.

### 3. Phase-1 fallback

The shared config API key/secret fallback should be considered retired. If any temporary local fallback is kept during implementation, it must be explicit, disabled by default, and removed from templates/docs before wider rollout.

---

## Auth and PAT Endpoints

Recommended endpoints:

```text
GET    /auth/google/login
GET    /auth/google/callback
POST   /auth/logout
GET    /me
GET    /auth/personal-access-tokens
POST   /auth/personal-access-tokens
POST   /auth/personal-access-tokens/{token_id}/revoke
```

### `GET /auth/google/login`

Query parameters:

```text
return_to=<dashboard-url>
```

Backend responsibilities:

- Validate `return_to` against allowed dashboard origins.
- Generate `state` and `nonce`.
- Store state/nonce server-side or in signed short-lived cookies.
- Redirect to Google with `openid email profile` scopes.

### `GET /auth/google/callback`

Backend responsibilities:

- Validate `state` and `nonce`.
- Exchange authorization code for tokens.
- Verify ID token.
- Enforce Workspace/domain policy.
- Upsert user and Google identity.
- Create dashboard web session.
- Set `HttpOnly`, `Secure`, `SameSite` cookie.
- Redirect to dashboard success URL.

### `POST /auth/personal-access-tokens`

Authenticated by dashboard web cookie.

Request:

```json
{
  "name": "Claude Code on MacBook",
  "client_type": "mcp",
  "expires_in_seconds": 7776000,
  "scopes": ["mcp"]
}
```

Response:

```json
{
  "id": "token-uuid",
  "name": "Claude Code on MacBook",
  "client_type": "mcp",
  "key_prefix": "engpat_live_ab12",
  "token": "engpat_live_ab12...full-secret-shown-once",
  "expires_at": "2026-10-02T00:00:00Z",
  "scopes": ["mcp"]
}
```

Backend responsibilities:

- Require authenticated web dashboard actor.
- Generate cryptographically random token.
- Hash token with server-side HMAC/pepper.
- Store token metadata and hash.
- Return raw token once.
- Never return raw token again from list/detail endpoints.

### `GET /auth/personal-access-tokens`

Authenticated by dashboard web cookie. Returns metadata only:

```json
[
  {
    "id": "token-uuid",
    "name": "Claude Code on MacBook",
    "client_type": "mcp",
    "key_prefix": "engpat_live_ab12",
    "created_at": "2026-07-04T00:00:00Z",
    "last_used_at": null,
    "expires_at": "2026-10-02T00:00:00Z",
    "revoked_at": null,
    "scopes": ["mcp"]
  }
]
```

### `POST /auth/personal-access-tokens/{token_id}/revoke`

Authenticated by dashboard web cookie.

Backend responsibilities:

- Ensure the token belongs to the current user unless the actor is admin.
- Mark token revoked.
- Do not delete the row; keep audit history.

### `GET /me`

Returns the current authenticated profile for both web cookie and PAT bearer clients:

```json
{
  "id": "user-uuid",
  "email": "user@1mg.com",
  "display_name": "User Name",
  "org_id": "org-uuid",
  "org_slug": "tata1mg",
  "client_type": "web",
  "auth_method": "oauth_web_cookie",
  "roles": ["user"]
}
```

---

## Dashboard Integration

Dashboard API migration should be mostly internal to the auth resolver:

```text
Before:
Dashboard request headers -> phase-1 AuthContextService -> ActorContext

After:
Dashboard cookie -> backend JWT/session verification -> ActorContext
```

Required dashboard changes:

- Redirect unauthenticated users to `/auth/google/login`.
- Use `credentials: include` for API calls.
- Call `/me` on app bootstrap.
- Add a settings page section for Personal Access Tokens:
  - list active/revoked tokens,
  - create token,
  - copy token once,
  - revoke token.
- Do not store the web JWT in localStorage.

---

## MCP Integration

Existing MCP tools already call:

```text
McpContextService.resolve_current_context()
    -> AuthContextService.resolve_actor_context(request)
```

So MCP migration should remain localized:

```text
Before:
MCP headers -> shared API key/secret + asserted email -> ActorContext

After:
MCP Authorization bearer PAT -> token hash lookup -> owning user/org -> ActorContext
```

Target Claude Code MCP config:

```json
{
  "mcpServers": {
    "engram": {
      "type": "http",
      "url": "https://api.example.com/mcp/http",
      "headers": {
        "Authorization": "Bearer ${ENGRAM_PERSONAL_ACCESS_TOKEN}",
        "X-Engram-Client": "claude-code"
      }
    }
  }
}
```

Repository metadata headers remain unchanged and should continue to be sent when available:

```text
X-Engram-Repository: <json metadata>
X-Engram-Repository-Origin-Url: <git origin url>
X-Engram-Repository-Path: <git root or basename>
X-Engram-Repository-Branch: <branch>
X-Engram-Repository-Commit: <commit sha>
```

`X-Engram-Repo` remains only a fallback hint.

Do not send these headers in the target MCP config:

```text
X-Engram-Api-Key
X-Engram-Api-Secret
X-Engram-User-Email
```

The backend derives the user from the PAT record.

---

## Personal Access Token Requirements

Raw PATs are bearer credentials. Treat them like passwords.

Validation rules:

- Require `Authorization: Bearer <token>`.
- Reject malformed token prefixes generically.
- Hash/HMAC full token before lookup.
- Verify token row exists.
- Verify token belongs to an active user and active org.
- Verify token is not expired.
- Verify token is not revoked.
- Verify token scopes/client type allow MCP access.
- Update `last_used_at` without blocking core request path if possible.

Storage rules:

- Never store raw token.
- Never log raw token.
- Never return raw token after creation response.
- Keep revoked token rows for audit.
- Use constant-time comparison if comparing hashes directly.

---

## RBAC and Audit Impact

RBAC should continue to use `ActorContext.roles` and `ActorContext.permissions`.

For MVP:

- `ADMIN_EMAILS` grants `admin` role.
- Everyone else with a valid `@1mg.com` Workspace identity receives `user`.
- PATs can start with a single broad `mcp` scope, then evolve into finer scopes later.

Audit logs should include:

- `auth_method`
- `client_type`
- `session_id` for web requests when available
- `personal_access_token_id` for MCP/PAT requests when available
- `request_id`
- `actor_user_id`
- `client_name`

This makes it possible to distinguish dashboard reads/writes from MCP tool calls by the same user.

---

## Failure Behavior

| Case | Response |
|---|---|
| Missing web cookie or bearer token | `401 Unauthorized` |
| Invalid web JWT signature/issuer/audience | `401 Unauthorized` |
| Expired web JWT/session | `401 Unauthorized` |
| Revoked web session | `401 Unauthorized` |
| Google callback state/nonce mismatch | `401 Unauthorized` |
| Google ID token cannot be verified | `401 Unauthorized` |
| `email_verified` is false | `403 Forbidden` |
| Email domain is not allowed | `403 Forbidden` |
| Hosted domain is present and not allowed | `403 Forbidden` |
| Missing/malformed PAT | `401 Unauthorized` |
| PAT hash not found | `401 Unauthorized` |
| PAT expired or revoked | `401 Unauthorized` |
| PAT scope does not allow MCP | `403 Forbidden` |
| User is disabled or blocked | `403 Forbidden` |
| Organization is disabled | `403 Forbidden` |
| Repo cannot be resolved | Continue without repo scope, or return `400` for tools that require repo scope |

Keep auth errors generic. Do not reveal whether a token, session ID, key prefix, or email policy check was the exact failing part unless it is safe and useful for the user-facing dashboard.

---

## Migration Plan

### Phase A: Keep `ActorContext` stable

Do not change memory services, RBAC services, MCP tools, or dashboard routers first. Preserve this boundary:

```text
request credential -> AuthContextService -> ActorContext -> services
```

### Phase B: Add models and config

1. Add `UserIdentity` model.
2. Add `Session` model for web sessions.
3. Add `PersonalAccessToken` model.
4. Add Google OAuth/JWT/cookie/PAT config fields.
5. Remove shared `API_KEY` and `API_SECRET` from auth config/templates.
6. Add `oauth_web_cookie` and `personal_access_token` auth method values.
7. Optionally add `session_id`, `personal_access_token_id`, and `client_type` to `ActorContext`.

### Phase C: Implement backend auth services

1. Add `google_oauth_service.py`.
2. Add `token_service.py` for backend web JWTs.
3. Add `session_service.py` for web sessions.
4. Add `personal_access_token_service.py` for PAT generation/hash/verification/revocation.
5. Add `user_identity_service.py` for user + Google identity upsert.
6. Refactor `AuthContextService` to dispatch between:
   - web cookie sessions,
   - PAT bearer tokens.

### Phase D: Add auth and PAT endpoints

1. `GET /auth/google/login`
2. `GET /auth/google/callback`
3. `POST /auth/logout`
4. `GET /me`
5. `GET /auth/personal-access-tokens`
6. `POST /auth/personal-access-tokens`
7. `POST /auth/personal-access-tokens/{token_id}/revoke`

Register auth/PAT routers in `main.py`.

### Phase E: Switch dashboard to cookie auth

1. Dashboard redirects users to `/auth/google/login`.
2. Backend sets the HttpOnly cookie.
3. Dashboard calls `/me` on load.
4. Existing dashboard API calls use `credentials: include`.
5. Remove phase-1 auth headers from dashboard requests.

### Phase F: Add dashboard PAT management

1. Add Settings → Personal Access Tokens UI.
2. Create/list/revoke PATs using dashboard web cookie auth.
3. Show raw PAT only once after creation.
4. Provide copyable MCP config instructions.

### Phase G: Switch MCP to PAT bearer auth

1. User creates PAT in dashboard.
2. User/plugin stores PAT in OS keychain or secure local config.
3. MCP config sends:

```text
Authorization: Bearer <personal-access-token>
```

4. Remove `X-Engram-Api-Key`, `X-Engram-Api-Secret`, and `X-Engram-User-Email` from MCP config.

### Phase H: Remove legacy phase-1 auth

1. Keep `MODE = google_workspace_oidc`.
2. Keep `PHASE1_HEADER_ENABLED = false`.
3. Remove shared API key/secret code paths.
4. Remove shared API key/secret references from user/plugin docs.

---

## Files Expected to Change During Implementation

Backend files likely to change or be added:

```text
models/identity.py                         -- add UserIdentity, Session, PersonalAccessToken
schemas/enums.py                           -- add auth methods/client types
schemas/context.py                         -- optional session_id/personal_access_token_id/client_type
schemas/auth.py                            -- login/me/PAT DTOs
services/config_service.py                 -- OAuth/JWT/cookie/PAT settings
services/auth_context_service.py           -- dispatcher for cookie/PAT
services/google_oauth_service.py           -- Google OAuth/OIDC flow
services/session_service.py                -- create/verify/revoke web sessions
services/token_service.py                  -- issue/verify backend web JWTs
services/personal_access_token_service.py  -- generate/hash/verify/revoke PATs
services/user_identity_service.py          -- user + Google identity upsert
routers/auth.py                            -- login/callback/logout/me
routers/personal_access_tokens.py          -- PAT create/list/revoke
routers/dependencies.py                    -- likely unchanged
services/mcp_context_service.py            -- likely unchanged
main.py                                    -- register auth/PAT routers
config_template.json                       -- auth config cleanup
pyproject.toml                             -- direct auth dependencies
```

Existing memory, proposal, tag, admin, audit, repository resolver, and MCP tool implementations should not need business-logic changes if `ActorContext` remains stable.

---

## Claude Code Plugin Distribution Recommendation

Preferred rollout path:

1. Package the Engram setup as an internal Claude Code plugin or installer.
2. Ask the user to create a PAT from the dashboard.
3. Store the PAT in the OS keychain where possible.
4. Generate or update local MCP config with the backend URL and PAT reference.
5. Keep manual `.mcp.json` setup as a fallback.

Target plugin/runtime config should need only:

```text
ENGRAM_PERSONAL_ACCESS_TOKEN
```

Sensitive values:

- `ENGRAM_PERSONAL_ACCESS_TOKEN` must be securely stored.
- No shared API secret should be required.
- No user email header should be required; the backend derives user identity from the PAT.

Suggested target `.mcp.json`:

```json
{
  "mcpServers": {
    "engram": {
      "type": "http",
      "url": "https://stag.deputydev.ai/engram-service/mcp/http",
      "headers": {
        "Authorization": "Bearer ${user_config.ENGRAM_PERSONAL_ACCESS_TOKEN}",
        "X-Engram-Client": "claude-code"
      }
    }
  }
}
```

If token interpolation is not available in the target Claude Code version, use a generated local config or wrapper script as the fallback.

---

## Definition of Done for Auth Migration

- [ ] Google Workspace OAuth login works locally.
- [ ] Backend verifies Google ID token and enforces `@1mg.com`.
- [ ] Unknown valid Workspace users can be auto-provisioned if enabled.
- [ ] Google `sub` is stored as the stable external identity.
- [ ] Web login creates a backend session and sets an HttpOnly Secure cookie.
- [ ] Dashboard `/me` works with cookie auth.
- [ ] Dashboard can create/list/revoke Personal Access Tokens.
- [ ] Raw PAT is shown only once and only token hash is stored.
- [ ] Existing dashboard APIs resolve `ActorContext` from cookie auth.
- [ ] Existing MCP tools resolve `ActorContext` from PAT bearer auth.
- [ ] PAT revocation works independently from web logout.
- [ ] Audit logs can distinguish web vs MCP requests.
- [ ] Shared config API key/secret auth is removed or disabled outside any temporary local migration branch.
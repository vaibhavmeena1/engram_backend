# Claude Desktop MCP OAuth MVP Plan

## Goal

Enable Claude Desktop to connect to the Engram remote MCP server using the Claude connector OAuth flow, while keeping the implementation **backend-only** for the MVP.

The fastest path is to add a thin OAuth facade on top of Engram's existing authentication model:

- **Google OAuth** remains the human login mechanism.
- **Engram web session cookie** remains the browser session credential after Google login.
- **Engram Personal Access Token (PAT)** remains the credential accepted by the MCP server.
- **New OAuth endpoints** are added only so Claude Desktop can complete its connector flow.
- The OAuth token exchange returns an **Engram PAT as the OAuth access token**.

This avoids building a separate identity provider and reuses the auth model already implemented in the backend.

---

## Constraints and Assumptions

### Current access constraints

Available routes/domains today:

- Backend access under: `https://stag.deputydev.ai/engram-service/*`
- Frontend access under: `https://stag.deputydev.ai/engram/*`
- No full control over `https://stag.deputydev.ai/*`

### Important implication

For the MVP, the OAuth metadata and OAuth endpoints should be hosted under:

- `https://stag.deputydev.ai/engram-service/.well-known/...`
- `https://stag.deputydev.ai/engram-service/oauth/...`

This should work **if Claude Desktop honors the `WWW-Authenticate` challenge header with `resource_metadata=...`**.

If Claude Desktop only probes root-level `/.well-known/...` endpoints and ignores the explicit header, then a later infrastructure change will be required to proxy:

- `/.well-known/oauth-protected-resource`
- `/.well-known/oauth-authorization-server`

into the Engram backend.

---

## Why We Need OAuth Even Though MCP Already Uses a Header Token

There are two different auth experiences:

### 1. Manual MCP config

This is the current Engram plugin approach:

- user manually gets or sets a token
- MCP config includes `Authorization: Bearer ${ENGRAM_PERSONAL_ACCESS_TOKEN}`
- Claude sends the token directly in the header

This does **not** require Claude Desktop connector OAuth.

### 2. Claude Desktop connector flow

When a user adds a remote connector in Claude Desktop, Claude wants to own the connection lifecycle:

- discover whether the remote MCP server is protected
- launch browser auth
- complete OAuth code flow
- store the resulting bearer token itself
- retry MCP calls with that token automatically

So even if the MCP server ultimately accepts a normal bearer token, Claude Desktop still expects the server to expose OAuth endpoints and metadata if it wants a "Connectors"-style login experience.

For the MVP, the OAuth layer is just a standard wrapper that eventually produces the same Engram PAT we already support.

---

## Existing Backend Capabilities We Can Reuse

The backend already has most of the core pieces:

- Google login flow
- backend-owned web session cookie
- PAT generation
- PAT storage and hashing
- PAT verification from `Authorization: Bearer <token>`
- MCP enforcement that requests use PAT-based auth

This means the missing work is **not** full auth from scratch.

The missing work is:

1. OAuth metadata discovery endpoints for Claude Desktop
2. OAuth client registration endpoint
3. OAuth authorize endpoint
4. OAuth token endpoint
5. MCP `401` challenge response with `WWW-Authenticate`

---

## MVP Architecture

```text
Claude Desktop
   |
   | request to remote MCP endpoint
   v
/engram-service/mcp/http
   |
   | 401 + WWW-Authenticate: Bearer resource_metadata=...
   v
/engram-service/.well-known/oauth-protected-resource
   |
   v
/engram-service/.well-known/oauth-authorization-server
   |
   v
/engram-service/oauth/authorize
   |
   | if not logged in
   v
/engram-service/auth/google/login
   |
   v
Google OAuth
   |
   v
/engram-service/auth/google/callback
   |
   v
/engram-service/oauth/authorize resumes
   |
   | create short-lived auth code
   v
redirect back to Claude redirect_uri?code=...
   |
   v
/engram-service/oauth/token
   |
   | validate code + PKCE
   | create Engram PAT
   v
return PAT as OAuth access_token
   |
   v
Claude Desktop retries MCP with Authorization: Bearer <engpat...>
```

---

## MVP Design Decisions

### 1. Backend-only for current phase

No new frontend screens are required in the MVP.

The authorization endpoint will:

- redirect to Google login if the user is not authenticated
- auto-approve after login
- generate authorization code
- redirect back to Claude

No separate consent UI is required in the current phase.

### 2. OAuth access token will be an Engram PAT

The `/oauth/token` endpoint will create a standard Engram PAT and return it as:

```json
{
  "access_token": "engpat_live_...",
  "token_type": "Bearer",
  "expires_in": 7776000,
  "scope": "mcp"
}
```

This keeps MCP verification unchanged because the server already knows how to verify Engram PAT bearer tokens.

### 3. Authorization code flow with PKCE only

For MVP, support only:

- `authorization_code`
- `PKCE (S256)`
- public clients
- no client secret
- no refresh token

### 4. Auto-approval for internal staging

Once a user is authenticated in Engram, the authorization request can be auto-approved.

This is acceptable for the MVP because:

- the environment is internal/staging
- the flow is for a specific Claude Desktop connector
- we are optimizing for speed and proof of integration

---

## Current Phase Scope

The current phase includes:

- backend endpoints for OAuth discovery and token flow
- backend changes to MCP unauthorized responses
- backend config additions
- backend DB changes for OAuth client and authorization-code support
- validation and rollout steps

The current phase does **not** include:

- a user-facing consent page
- refresh tokens
- token revocation via OAuth endpoints
- frontend work
- broad infrastructure changes outside `engram-service`
- multi-provider OAuth or non-Google login

---

## Required Backend Endpoints

## 1. Protected resource metadata

### Endpoint

`GET /engram-service/.well-known/oauth-protected-resource`

### Purpose

Tell Claude Desktop that the MCP resource is protected and which authorization server it should use.

### Example response

```json
{
  "resource": "https://stag.deputydev.ai/engram-service/mcp/http",
  "authorization_servers": [
    "https://stag.deputydev.ai/engram-service"
  ],
  "scopes_supported": ["mcp"],
  "bearer_methods_supported": ["header"]
}
```

### Notes

- `resource` should match the actual MCP HTTP endpoint.
- `authorization_servers` should point at the Engram backend base URL.
- Keep the surface minimal for MVP.

---

## 2. Authorization server metadata

### Endpoint

`GET /engram-service/.well-known/oauth-authorization-server`

### Purpose

Expose the OAuth server endpoints Claude Desktop needs for discovery.

### Example response

```json
{
  "issuer": "https://stag.deputydev.ai/engram-service",
  "authorization_endpoint": "https://stag.deputydev.ai/engram-service/oauth/authorize",
  "token_endpoint": "https://stag.deputydev.ai/engram-service/oauth/token",
  "registration_endpoint": "https://stag.deputydev.ai/engram-service/oauth/register",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code"],
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": ["none"],
  "scopes_supported": ["mcp"]
}
```

### Notes

- No refresh token support is needed now.
- No client secret support is needed now.
- If Claude later expects additional metadata keys, they can be added without changing the core design.

---

## 3. Dynamic client registration

### Endpoint

`POST /engram-service/oauth/register`

### Purpose

Allow Claude Desktop to register itself as a public OAuth client if it chooses to do so.

### MVP behavior

- accept a client registration request
- validate basic fields
- create or upsert a client record
- return a public client response

### Example response

```json
{
  "client_id": "engram_claude_desktop",
  "client_name": "Claude Desktop",
  "redirect_uris": [
    "https://claude.ai/api/mcp/auth_callback"
  ],
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```

### MVP simplification

It is acceptable to start with one of these strategies:

1. **Hardcoded public Claude client** for staging
2. **DB-backed client registration** with minimal schema

Recommended choice for MVP:

- support DB-backed registration
- allow only `https://claude.ai/*` redirect URIs
- treat all clients as public clients

This is slightly more work than hardcoding but is much safer and easier to evolve.

---

## 4. Authorization endpoint

### Endpoint

`GET /engram-service/oauth/authorize`

### Expected inputs

Typical OAuth authorize params:

- `response_type=code`
- `client_id`
- `redirect_uri`
- `state`
- `scope=mcp`
- `code_challenge`
- `code_challenge_method=S256`
- optional `resource`

### MVP behavior

1. Validate request shape.
2. Validate client exists and redirect URI is allowed.
3. Validate `response_type=code`.
4. Validate `code_challenge_method=S256`.
5. Validate scope includes `mcp`.
6. If user is not logged into Engram:
   - redirect to existing Google login route
   - set `return_to` as the full authorize URL
7. After login:
   - resolve current web-session actor
   - create a short-lived authorization code
   - auto-approve the request
   - redirect back to Claude with `code` and `state`

### Notes

- No separate consent page in the MVP.
- Authorization codes should expire quickly, e.g. 5 minutes.
- The request should be tied to the exact `client_id`, `redirect_uri`, `scope`, and `code_challenge` used during authorization.

---

## 5. Token endpoint

### Endpoint

`POST /engram-service/oauth/token`

### Expected inputs

- `grant_type=authorization_code`
- `code`
- `client_id`
- `redirect_uri`
- `code_verifier`

### MVP behavior

1. Validate the authorization code.
2. Ensure it is not expired or already used.
3. Validate `client_id` and `redirect_uri` match the authorization request.
4. Validate PKCE using the provided `code_verifier`.
5. Resolve the associated Engram user and org.
6. Create an Engram PAT using the existing `PersonalAccessTokenService`.
7. Return the raw PAT as the OAuth access token.

### Example response

```json
{
  "access_token": "engpat_live_xxxxxxxxxxxxxxxxx",
  "token_type": "Bearer",
  "expires_in": 7776000,
  "scope": "mcp"
}
```

### Notes

- Reuse existing PAT TTL rules where possible.
- For MVP, no refresh token is needed.
- Token revocation remains PAT revocation, not OAuth refresh-token revocation.

---

## Required MCP Behavior Change

## Return proper OAuth challenge when unauthenticated

When the MCP HTTP endpoint receives a request without a valid bearer token, it must return a `401 Unauthorized` with a `WWW-Authenticate` header.

### Required header

```http
WWW-Authenticate: Bearer resource_metadata="https://stag.deputydev.ai/engram-service/.well-known/oauth-protected-resource", error="invalid_token", error_description="Missing or invalid access token"
```

### Why this matters

This is the most important discovery step for Claude Desktop because we do not currently control root-level `/.well-known/...` routes on `stag.deputydev.ai`.

If Claude Desktop honors the explicit `resource_metadata` URL from this header, it can discover the OAuth metadata under `/engram-service/.well-known/...` without any additional infra work.

---

## Required DB Changes in Current Phase

## Table 1: OAuth clients

Add a table for registered OAuth clients.

### Suggested table

`engram_oauth_clients`

### Suggested columns

```text
id UUID PRIMARY KEY
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
client_id VARCHAR(255) NOT NULL UNIQUE
client_name VARCHAR(255) NULL
redirect_uris JSONB NOT NULL DEFAULT '[]'::jsonb
grant_types JSONB NOT NULL DEFAULT '["authorization_code"]'::jsonb
response_types JSONB NOT NULL DEFAULT '["code"]'::jsonb
token_endpoint_auth_method VARCHAR(64) NOT NULL DEFAULT 'none'
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
last_seen_at TIMESTAMPTZ NULL
```

### Why include it in MVP

- supports dynamic client registration cleanly
- avoids hardcoding Claude-specific assumptions into the business logic
- gives auditability and room for later expansion

---

## Table 2: OAuth authorization codes

Add a table for short-lived authorization codes.

### Suggested table

`engram_oauth_authorization_codes`

### Suggested columns

```text
id UUID PRIMARY KEY
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
expires_at TIMESTAMPTZ NOT NULL
used_at TIMESTAMPTZ NULL
code_hash VARCHAR(128) NOT NULL UNIQUE
client_id VARCHAR(255) NOT NULL
redirect_uri TEXT NOT NULL
scope VARCHAR(255) NOT NULL DEFAULT 'mcp'
code_challenge VARCHAR(255) NOT NULL
code_challenge_method VARCHAR(16) NOT NULL DEFAULT 'S256'
resource TEXT NULL
user_id UUID NOT NULL
org_id UUID NOT NULL
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

### Why DB-backed codes are recommended

A stateless signed authorization code is possible, but a DB-backed code is better for MVP because it gives:

- one-time-use enforcement
- easier debugging
- easier revocation during testing
- easier audit trail
- simpler logic for future consent screens and approval history

### MVP simplification

Hash the raw authorization code before storing it, similar to PAT handling.

---

## Config Changes Required in Current Phase

Add a new config block, or extend the existing auth config.

Recommended approach: add a dedicated OAuth block to keep the existing auth settings readable.

## Suggested config shape

```json
{
  "ENGRAM_OAUTH": {
    "ENABLED": true,
    "ISSUER": "https://stag.deputydev.ai/engram-service",
    "PUBLIC_BASE_URL": "https://stag.deputydev.ai/engram-service",
    "MCP_RESOURCE_URL": "https://stag.deputydev.ai/engram-service/mcp/http",
    "AUTHORIZATION_ENDPOINT_PATH": "/oauth/authorize",
    "TOKEN_ENDPOINT_PATH": "/oauth/token",
    "REGISTRATION_ENDPOINT_PATH": "/oauth/register",
    "PROTECTED_RESOURCE_METADATA_PATH": "/.well-known/oauth-protected-resource",
    "AUTHORIZATION_SERVER_METADATA_PATH": "/.well-known/oauth-authorization-server",
    "AUTHORIZATION_CODE_TTL_SECONDS": 300,
    "DEFAULT_MCP_ACCESS_TOKEN_TTL_SECONDS": 7776000,
    "ALLOWED_REDIRECT_URI_ORIGINS": [
      "https://claude.ai"
    ],
    "ALLOW_DYNAMIC_CLIENT_REGISTRATION": true,
    "AUTO_APPROVE_TRUSTED_CLIENTS": true,
    "TRUSTED_CLIENT_NAMES": [
      "Claude Desktop",
      "Claude Code"
    ],
    "AUTHORIZATION_CODE_HASH_SECRET": ""
  }
}
```

## Config notes

- `AUTHORIZATION_CODE_HASH_SECRET` should be treated like a deployment secret.
- `ALLOWED_REDIRECT_URI_ORIGINS` should be strict in MVP.
- `AUTO_APPROVE_TRUSTED_CLIENTS` keeps the current phase backend-only.
- `DEFAULT_MCP_ACCESS_TOKEN_TTL_SECONDS` should align with PAT policy unless there is a reason to shorten OAuth-issued PATs.

---

## Suggested Backend File Changes

This section maps the MVP work to likely backend files.

## New router files

### `app/routers/oauth.py`

Add routes for:

- `GET /.well-known/oauth-protected-resource`
- `GET /.well-known/oauth-authorization-server`
- `POST /oauth/register`
- `GET /oauth/authorize`
- `POST /oauth/token`

This should remain separate from `app/routers/auth.py` because:

- `auth.py` is for Engram's own login/session flow
- `oauth.py` is the external OAuth facade for MCP connectors

---

## New service files

### `app/services/oauth_client_service.py`

Responsibilities:

- register or upsert OAuth clients
- validate client existence
- validate redirect URIs
- track last seen time

### `app/services/oauth_authorization_service.py`

Responsibilities:

- validate authorize requests
- build login redirect to existing Google login flow
- create authorization codes
- redeem authorization codes
- validate PKCE
- generate redirect back to Claude

### `app/services/oauth_metadata_service.py`

Responsibilities:

- build protected resource metadata response
- build authorization server metadata response
- centralize URL building from config

These services should stay focused and avoid putting OAuth logic directly into `mcp_router.py` or `auth.py`.

---

## Existing files likely to change

### `app/main.py`

- register the new `oauth` router

### `app/services/config_service.py`

- add config model for `ENGRAM_OAUTH`

### `config_template.json`

- add `ENGRAM_OAUTH` settings

### `config.json`

- optionally add local/staging sample values if this repo tracks usable local config

### `app/routers/mcp_router.py`

- ensure unauthorized MCP responses become proper HTTP `401`
- add `WWW-Authenticate` header with `resource_metadata`

### `app/services/personal_access_token_service.py`

Possible addition:

- helper for creating OAuth-issued PATs with a standard naming pattern, for example:
  - `Claude Desktop OAuth`
  - or `Claude Desktop on <hostname>` if a name can be derived later

### `app/schemas/auth.py`

Add request/response schemas for:

- OAuth client registration
- authorize request params
- token exchange request/response
- metadata response shapes

---

## PAT Naming for OAuth-Issued Tokens

Use a predictable PAT display name pattern.

### Suggested naming

- `Claude Desktop OAuth`
- `Claude Desktop Connector`

If later phases add richer client metadata, the name can become:

- `Claude Desktop on MacBook Pro`
- `Claude Desktop - Vaibhav's laptop`

For the MVP, keep the name simple and stable.

---

## Detailed MVP Implementation Steps

## Step 1: Add config support

1. Add `ENGRAM_OAUTH` config model in `app/services/config_service.py`
2. Add defaults in `config_template.json`
3. Add staging values for:
   - issuer
   - public base URL
   - MCP resource URL
   - allowed redirect URI origins
   - authorization code TTL
   - hash secret

### Done when

- config loads cleanly
- app boots with OAuth settings enabled

---

## Step 2: Add DB migrations

1. Create migration for `engram_oauth_clients`
2. Create migration for `engram_oauth_authorization_codes`
3. Add indexes for:
   - `client_id`
   - `code_hash`
   - `expires_at`
   - `used_at`
   - `user_id`, `org_id`

### Done when

- migrations apply successfully
- rollback path exists

---

## Step 3: Add OAuth metadata endpoints

1. Implement protected resource metadata endpoint
2. Implement authorization server metadata endpoint
3. Build URLs from config rather than hardcoding them inline

### Done when

- `curl` returns valid JSON for both endpoints
- values match staging domain and MCP path

---

## Step 4: Add client registration endpoint

1. Implement request schema
2. Validate redirect URIs are under allowed origins
3. Save or upsert client record
4. Return public-client registration response

### Done when

- Claude Desktop can register a client
- redirect URI validation works

---

## Step 5: Add authorization endpoint

1. Validate OAuth authorize params
2. Load client and validate redirect URI
3. If no Engram session cookie exists:
   - redirect to `/auth/google/login?return_to=<full authorize url>`
4. If session exists:
   - validate actor is authenticated via web session
   - auto-approve request
   - create auth code row
   - redirect to Claude with `code` and `state`

### Done when

- manual browser test can round-trip through Google login and return a code

---

## Step 6: Add token endpoint

1. Validate token exchange params
2. Look up hashed authorization code
3. Ensure code is active and unused
4. Validate PKCE verifier against stored challenge
5. Mark code as used
6. Create Engram PAT using existing PAT service
7. Return PAT as OAuth access token

### Done when

- token exchange succeeds
- returned token is accepted by MCP as bearer auth

---

## Step 7: Update MCP unauthorized response

1. Return HTTP `401` instead of a generic auth failure payload when the transport-level request is unauthenticated
2. Add `WWW-Authenticate` challenge header
3. Point `resource_metadata` to `/engram-service/.well-known/oauth-protected-resource`

### Done when

- `curl -i` shows the correct header on unauthorized MCP requests

---

## Step 8: End-to-end manual validation

### Manual checks

1. Import the connector/plugin into Claude Desktop
2. Attempt to enable the connector
3. Confirm browser opens
4. Confirm user is redirected through Engram Google login if needed
5. Confirm callback ends at Claude success URL
6. Confirm Claude retries MCP calls with bearer token
7. Confirm MCP tools succeed

### CLI checks

```bash
curl -i https://stag.deputydev.ai/engram-service/mcp/http
curl https://stag.deputydev.ai/engram-service/.well-known/oauth-protected-resource
curl https://stag.deputydev.ai/engram-service/.well-known/oauth-authorization-server
```

---

## Security Notes for MVP

Even though this is an MVP, these should still be enforced now:

- require `PKCE S256`
- allow only `https://claude.ai` redirect origins
- expire authorization codes quickly
- mark authorization codes single-use
- hash stored authorization codes
- keep PAT hashing unchanged
- keep Google login/session handling unchanged
- do not expose raw internal exceptions in OAuth callback failures
- keep OAuth endpoints separate from internal auth/session services

---

## Risks and Fallbacks

## Risk 1: Claude does not honor path-scoped metadata discovery

### Symptom

Claude Desktop fails to discover OAuth metadata under `/engram-service/.well-known/...` even when `WWW-Authenticate` includes `resource_metadata=...`.

### Fallback

Request infra support for only these two proxy routes at the root domain:

- `https://stag.deputydev.ai/.well-known/oauth-protected-resource`
- `https://stag.deputydev.ai/.well-known/oauth-authorization-server`

Proxy them to the Engram backend routes.

This is a small infrastructure ask compared with needing broad root-domain control.

---

## Risk 2: Claude expects more registration metadata

### Symptom

Claude registration fails because it expects more fields in the registration response.

### Fallback

Expand the registration schema without changing the rest of the design.

This should be low-risk because the OAuth wrapper is intentionally isolated.

---

## Risk 3: OAuth-issued PAT sprawl

### Symptom

Repeated connector attempts create many PATs for the same user.

### MVP handling

Accept this in the first pass if needed.

### Better handling soon after MVP

- attach metadata like client_id and redirect_uri to the token
- optionally reuse a non-revoked connector PAT for the same user/client combination

---

## Recommended Order of Execution

1. Config changes
2. DB migrations
3. OAuth metadata endpoints
4. Client registration endpoint
5. Authorization endpoint
6. Token endpoint
7. MCP unauthorized-response update
8. End-to-end Claude Desktop validation
9. Small fixes from real connector behavior

This order gives quick feedback early, especially around metadata discovery and unauthorized challenge behavior.

---

## What Later Phases Should Add

## Phase 2: Consent screen and approval UX

Add a frontend consent page under `engram/*`.

### Additions

- consent screen showing client name, scope, and resource
- allow/deny action
- approval record storage
- skip approval for previously approved clients

### Why later

Not required for initial connector success.

---

## Phase 3: Better token lifecycle

### Additions

- refresh token support
- OAuth token revocation endpoint
- stable reuse of connector PATs where appropriate
- short-lived access token + refresh token design if desired

### Note

This phase may move from returning PATs directly to returning OAuth-native access tokens that map internally to a PAT or session record.

---

## Phase 4: Smarter client identity and policy

### Additions

- stronger dynamic client registration validation
- trusted-client allowlist by issuer or metadata
- per-client policy rules
- device naming and richer client display info
- separate rules for Claude Desktop vs Claude Code vs future clients

---

## Phase 5: Infra hardening

### Additions

- root-level `/.well-known/...` proxy if required
- dedicated auth subdomain if needed later
- monitoring and alerting for OAuth failures
- structured audit logs for authorize/token events

---

## Phase 6: Frontend and account management

### Additions

- dashboard page listing OAuth-connected clients
- revoke connector-issued tokens from UI
- show last used time and device information
- explain to users the difference between manual PATs and connector-based auth

---

## Open Questions to Resolve During Implementation

1. Does Claude Desktop honor `resource_metadata` from the MCP `WWW-Authenticate` header for path-scoped metadata URLs?
2. What exact redirect URI does Claude Desktop send in registration/authorize on the current product surface?
3. Does Claude Desktop always perform dynamic client registration, or can it use a stable public client?
4. Does Claude Desktop require any extra metadata fields beyond the minimum authorization server metadata listed above?
5. Should OAuth-issued PATs use the normal PAT TTL or a shorter dedicated TTL?

These do not block implementation, but they should be answered during staging validation.

---

## Final Recommendation

For the MVP, implement a **backend-only OAuth facade** that:

- exposes OAuth discovery under `engram-service`
- uses Google login + Engram web session for the browser-authenticated user
- issues short-lived authorization codes with PKCE
- returns an Engram PAT as the OAuth access token
- keeps MCP validation unchanged
- updates MCP unauthorized responses to advertise OAuth metadata

This is the fastest path to a Claude Desktop connector experience with the least architectural churn.

It also gives a clean base for later phases like consent UI, refresh tokens, token revocation, and connector management.
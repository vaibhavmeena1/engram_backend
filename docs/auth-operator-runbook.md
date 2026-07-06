# Auth Operator Runbook

## Required production secrets

Set these from the deployment secret manager, not from committed config:

- `ENGRAM_AUTH.GOOGLE_CLIENT_SECRET`
- `ENGRAM_AUTH.JWT_SIGNING_KEY`
- `ENGRAM_AUTH.PERSONAL_ACCESS_TOKEN_HASH_SECRET`

Rotate these with a planned maintenance window because active dashboard sessions and Personal Access Tokens depend on them.

## Cookie and CSRF checklist

For same-site dashboard/API deployments, keep:

- `SESSION_COOKIE_HTTP_ONLY=true`
- `SESSION_COOKIE_SECURE=true` in production HTTPS environments
- `SESSION_COOKIE_SAME_SITE=lax` or `strict`

If the dashboard and API become cross-site and require `SESSION_COOKIE_SAME_SITE=none`, also set:

- `SESSION_COOKIE_SECURE=true`
- `CSRF_PROTECTION_ENABLED=true`

The dashboard sends the `engram_csrf` cookie value back in `x-engram-csrf` for state-changing requests.

## Personal Access Token revocation

Preferred path:

1. Ask the user to open Dashboard → Settings → Personal Access Tokens.
2. Revoke the affected token.
3. Ask the user to create a replacement token and update local MCP config.

Emergency database path:

```sql
UPDATE engram_personal_access_tokens
SET revoked_at = NOW(), revoked_reason = 'operator_revocation'
WHERE id = '<personal-access-token-id>';
```

Do not delete token rows; keeping them preserves audit history.

## Auth failure debugging

Use audit logs and request metadata to distinguish dashboard and MCP failures:

- `auth_method`
- `client_type`
- `session_id`
- `personal_access_token_id`
- `actor_user_id`
- `request_id`
- `client_name`

Common checks:

1. `401 Invalid bearer token`: token missing, malformed, revoked, expired, or hash secret mismatch.
2. `403 Bearer token scope is not allowed`: PAT is valid, but missing the required MCP scope.
3. `403 Personal Access Token client type is not allowed for MCP`: token is valid, but not an MCP/CLI/automation-compatible client type.
4. `401 Invalid session token`: dashboard cookie is missing, expired, revoked, signed with another JWT key, or has invalid issuer/audience.
5. `403 CSRF token is missing or invalid`: cross-site cookie mode is enabled and the dashboard did not echo the CSRF cookie in the configured CSRF header.
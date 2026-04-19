# PHASE 0.2 — Telegram Auth + JWT + User Quotas

## Scope
Add user authentication via Telegram Login Widget, JWT token management, and per-user translation quotas.

## Architecture Changes

### New Models
| Model | Fields |
|-------|--------|
| `User` | id (UUID), telegram_id (unique), username, display_name, avatar_url, is_admin, quota_chars_total, quota_chars_used, quota_reset_at, created_at, last_login_at |
| `AuthToken` | id, user_id (FK), token_hash, expires_at, created_at, revoked |

### New Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/telegram` | public | Validate Telegram auth data, create/login user, return JWT |
| POST | `/auth/refresh` | public | Refresh expired JWT using refresh token |
| POST | `/auth/logout` | JWT | Revoke current token |
| GET | `/auth/me` | JWT | Return current user profile + quota status |
| GET | `/admin/users` | admin | List all users (admin only) |
| PATCH | `/admin/users/{id}/quota` | admin | Reset/adjust user quota |

### Quota System
- Default: 500,000 chars/month per user
- Admins: unlimited
- Tracked via `chars_translated` on Task model (already exists)
- Monthly reset via cron on the 1st
- Upload endpoint rejects when quota exceeded (429)

### JWT Config
- Algorithm: HS256
- Access token TTL: 24h
- Refresh token TTL: 30d
- Secret from `.env` (`JWT_SECRET`)
- Payload: `{sub: user_id, role: "user"|"admin", exp, iat}`

### Telegram Login Flow
1. Frontend renders Telegram Login Widget (via `https://oauth.telegram.org/auth`)
2. Widget POSTs auth data to `/auth/telegram`
3. Backend validates `hash` using SHA256-HMAC of bot token
4. Finds or creates `User` by `telegram_id`
5. Returns `{access_token, refresh_token, user}`

## Files to Create/Modify
| Action | File |
|--------|------|
| Create | `shared/auth.py` — JWT encode/decode, Telegram hash verification |
| Create | `shared/schemas.py` — Pydantic request/response models |
| Modify | `shared/models.py` — Add User, AuthToken models |
| Modify | `shared/database.py` — No changes needed |
| Modify | `shared/config.py` — Add JWT_SECRET, TELEGRAM_BOT_DOMAIN |
| Create | `core/middleware.py` — JWT auth dependency, admin guard |
| Modify | `core/routes.py` — Add auth routes, protect upload/status/download |
| Modify | `worker/engine.py` — Add quota check before processing |
| Create | `tests/test_auth.py` — Auth flow tests |
| Create | `tests/test_quotas.py` — Quota enforcement tests |
| Modify | `.env` — Add JWT_SECRET, DEFAULT_QUOTA_CHARS, TELEGRAM_BOT_DOMAIN |

## Dependencies
- `PyJWT` (or `python-jose`) — JWT encoding
- `passlib` — Not needed (Telegram auth, no passwords)
- No new system deps

## Migration
- SQLite doesn't support ALTER TABLE well — use `Base.metadata.create_all()` for new tables
- Existing tasks need `user_id` column (nullable for backward compat)

## Cron Additions
- Monthly quota reset: `quota_chars_used = 0, quota_reset_at = NOW() + 1 month`

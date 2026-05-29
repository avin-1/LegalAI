---
title: LegalAI Login Gateway
emoji: 🔐
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# LegalAI Login API (Hugging Face Space)

Public **HTTPS** hits the **api-gateway** on the Space port (default **7860**; the platform may set **`PORT`** — `start.sh` binds **`0.0.0.0:$PORT`** when present). The gateway proxies **`/api/auth/*`** to the **auth-service** (SQLite + Redis) and can optionally proxy **`/embed/*`** and **`/graph/*`** when those URLs are configured.

## Required secrets (Space variables)

Set these in the Space **Settings → Repository secrets** (or **Variables**), not in the repo:

| Variable | Purpose |
|----------|---------|
| `REDIS_URL` | Redis URL: `redis://` or **`rediss://`** (TLS). Trust store uses **OS CA bundle** (`ca-certificates` in the image). |
| `REDIS_TLS_INSECURE` | Set to `1` if TLS to your provider fails (e.g. strict SNI). Disables certificate verification — **last resort**. |
| `JWT_SECRET` | At least **32** characters. Generate locally: `openssl rand -hex 32`. |

Optional but recommended for defense in depth:

| Variable | Purpose |
|----------|---------|
| `INTERNAL_EXCHANGE_SECRET` | Same value on both processes; enables `x-internal-secret` on token exchange. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed browser origins (if unset, all origins are allowed). |

**Avoid** a Space secret named **`LISTEN_ADDR`** unless you know what it does: it is injected into **both** processes. The **auth** service only reads **`AUTH_LISTEN_ADDR`** (default `0.0.0.0:3001`); the **gateway** port comes from **`PORT`** / `start.sh`. Delete **`LISTEN_ADDR`** if you added it for the public port — use repository **`README` `app_port`** and the platform **`PORT`** instead.

## Optional

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Leave **unset** on Spaces: `start.sh` uses **`sqlite:///data/auth.db`** (writable dir from the image), or **`sqlite:///tmp/...`** if `/data` is not writable. Do **not** point at the app folder if the Space mounts it read-only (SQLite error 14). Override only with a known-writable absolute path. |
| `EMBEDDING_API_URL` | Enables `/embed/*` proxying. |
| `GRAPH_API_URL` | Enables `/graph/*` proxying. |
| `JWT_EXPIRY_SECS` | JWT lifetime in seconds (default `300`). |
| `OPAQUE_TOKEN_TTL_SECS` | Opaque session token TTL in Redis (default `3600`). |

## Health checks

- Gateway: `GET /health` (liveness), `GET /ready` (checks auth `/ready`).
- Auth (internal): `GET /health`, `GET /ready` (SQLite + Redis).

## API (via gateway, port 7860)

- `POST /api/auth/signup` — JSON `{ "username", "password" }`
- `POST /api/auth/login` — JSON `{ "username", "password" }`
- `DELETE /api/auth/logout` — JSON `{ "opaque_token" }` (same shape as `ExchangeRequest` in code)

Authenticated calls use header `Authorization: Bearer <opaque_token>`; the gateway exchanges it for a short-lived JWT before proxying to `/embed` or `/graph`.

## Render Redis + Hugging Face

Render’s **external** Redis URL uses **`rediss://`** (TLS). Two common blockers:

1. **Networking** — In Render’s Redis **Networking** / inbound access, allow connections from the internet (for Spaces, often **`0.0.0.0/0`** while testing). If inbound is locked down, the Space will never reach Redis.
2. **TLS** — If you still see TLS or certificate errors after redeploying this repo, add a Space secret **`REDIS_TLS_INSECURE=1`** (disables verification; use only if needed).

## Persistence

By default SQLite is under **`/data/auth.db`** (or `/tmp/...` as fallback). Container restarts or redeploys can still wipe it unless the Space uses persistent storage or you use an external database. Remove any **`DATABASE_URL`** secret that targets the read-only app directory.

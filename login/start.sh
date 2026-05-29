#!/bin/sh
set -eu

# Hugging Face (and some Docker entrypoints) may run this script with a cwd that is
# not writable. SQLite then fails with "unable to open database file" (code 14) for
# relative paths like sqlite:auth.db. Always run from the app directory and use an
# absolute DB URL by default.
HOME="${HOME:-/home/user}"
APP_DIR="${APP_DIR:-$HOME/app}"
cd "$APP_DIR" || {
  echo "Cannot cd to APP_DIR=$APP_DIR (set APP_DIR or HOME to a writable app directory)."
  exit 1
}

# SQLite: Hugging Face often serves the app directory read-only, so a DB next to the
# binaries fails with SQLITE_CANTOPEN (14). Prefer /data (created + chown in Dockerfile),
# then fall back to /tmp (always writable).
if [ -z "${DATABASE_URL:-}" ]; then
  DATA_DIR="${DATA_DIR:-/data}"
  if mkdir -p "$DATA_DIR" 2>/dev/null && touch "$DATA_DIR/.write_probe" 2>/dev/null; then
    rm -f "$DATA_DIR/.write_probe"
    # sqlx: sqlite:// + absolute path  →  sqlite:///path/to/file
    export DATABASE_URL="sqlite://$DATA_DIR/auth.db"
  else
    SQLITE_DIR="${TMPDIR:-/tmp}/legalai-sqlite"
    mkdir -p "$SQLITE_DIR"
    export DATABASE_URL="sqlite://$SQLITE_DIR/auth.db"
    echo "Note: $DATA_DIR not writable; using DATABASE_URL=$DATABASE_URL"
  fi
fi
echo "Effective DATABASE_URL=$DATABASE_URL"

# --- Pre-flight Checks (Hardcoded Secrets) ---
# Hardcoding as requested by user
export JWT_SECRET="${JWT_SECRET:-my_super_secret_legal_ai_key_2026}"
export REDIS_URL="${REDIS_URL:-rediss://red-d5b6kmf5r7bs73a6l3bg:CG2FJzHUlfAFZkFNry1ByrcK5va2ni5x@singapore-keyvalue.render.com:6379}"

# Render Redis often needs this for cert verification bypass with rediss://
export REDIS_TLS_INSECURE=1

if [ -z "$JWT_SECRET" ]; then
  echo "ERROR: JWT_SECRET is missing."
  exit 1
fi
if [ -z "$REDIS_URL" ]; then
  echo "ERROR: REDIS_URL is missing."
  exit 1
fi

# Auth binds an internal port only.
export AUTH_LISTEN_ADDR="${AUTH_LISTEN_ADDR:-0.0.0.0:3001}"

echo "Starting auth-service on $AUTH_LISTEN_ADDR ..."
# Use /tmp for logs because the app directory might be read-only
AUTH_LOG="/tmp/auth_service.log"
rm -f "$AUTH_LOG"
./auth-service > "$AUTH_LOG" 2>&1 &
AUTH_PID=$!

# Hugging Face may set PORT; default public port for Docker Spaces is 7860.
GATEWAY_PORT="${PORT:-7860}"

i=0
AUTH_READY=0
while [ "$i" -lt 90 ]; do
  if ! kill -0 "$AUTH_PID" 2>/dev/null; then
    echo "--- auth-service CRASHED during startup ---"
    echo "Last logs from $AUTH_LOG:"
    if [ -f "$AUTH_LOG" ]; then
      cat "$AUTH_LOG"
    else
      echo "(Log file not found or empty)"
    fi
    echo "------------------------------------------"
    echo "Common causes: JWT_SECRET < 32 chars, bad REDIS_URL format, or firewall/TLS issues."
    set +e
    wait "$AUTH_PID"
    EXIT=$?
    set -e
    echo "auth-service exit code: $EXIT"
    exit 1
  fi
  if curl -sf "http://127.0.0.1:3001/health" >/dev/null 2>&1; then
    AUTH_READY=1
    break
  fi
  i=$((i + 1))
  sleep 1
done

if [ "$AUTH_READY" != 1 ]; then
  echo "--- auth-service TIMED OUT (failed to become healthy within 90s) ---"
  echo "Last logs:"
  cat auth_service.log
  echo "----------------------------------------------------------------"
  echo "Check if Redis is reachable and if REDIS_URL is correct."
  kill "$AUTH_PID" 2>/dev/null || true
  set +e
  wait "$AUTH_PID"
  set -e
  exit 1
fi

export LISTEN_ADDR="0.0.0.0:${GATEWAY_PORT}"
export AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://127.0.0.1:3001}"

echo "Starting api-gateway on $LISTEN_ADDR (PORT=${GATEWAY_PORT}) ..."
exec ./api-gateway

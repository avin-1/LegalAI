# ── Stage 1: Build ────────────────────────────────────────────────────────────
# Cache bust: 2026-04-05-v3
FROM rust:1-slim AS builder

# Install build deps for sqlx (needs OpenSSL / pkg-config / sqlite3)
RUN apt-get update && apt-get install -y pkg-config libssl-dev libsqlite3-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy workspace manifests and lockfile for layer caching
COPY Cargo.toml Cargo.lock ./
COPY shared/Cargo.toml shared/Cargo.toml
COPY auth-service/Cargo.toml auth-service/Cargo.toml
COPY api-gateway/Cargo.toml api-gateway/Cargo.toml

# Stub sources so cargo can resolve the dependency graph
RUN mkdir -p shared/src auth-service/src api-gateway/src \
    && echo "pub mod errors; pub mod jwt_middleware; pub mod models;" > shared/src/lib.rs \
    && touch shared/src/errors.rs shared/src/jwt_middleware.rs shared/src/models.rs \
    && echo "fn main(){}" > auth-service/src/main.rs \
    && echo "fn main(){}" > api-gateway/src/main.rs

RUN cargo build --release 2>/dev/null || true

# Now copy real sources and build properly
COPY . .

RUN cargo build --release

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y ca-certificates curl libsqlite3-0 libssl3 && rm -rf /var/lib/apt/lists/*

# HF Spaces runs as a non-root user (uid 1000).
# The Space often mounts the app tree read-only; SQLite must use a writable path (/data or /tmp).
RUN useradd -m -u 1000 user \
    && mkdir -p /data \
    && chown user:user /data \
    && chmod a+rwx /data
USER user
ENV HOME=/home/user
ENV DATA_DIR=/data
WORKDIR $HOME/app

# Copy binaries
COPY --from=builder --chown=user /build/target/release/auth-service  ./auth-service
COPY --from=builder --chown=user /build/target/release/api-gateway   ./api-gateway

# Copy migrations so sqlx can run them at startup
COPY --chown=user auth-service/migrations ./migrations

# Startup script — runs auth-service in background, gateway in foreground
COPY --chown=user start.sh ./start.sh
RUN chmod +x ./start.sh

# HF Spaces exposes port 7860
EXPOSE 7860

CMD ["./start.sh"]

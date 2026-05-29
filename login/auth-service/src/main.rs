mod config;
mod cache;
mod db;
mod handlers;
mod token;

use std::sync::Arc;

use axum::{
    extract::DefaultBodyLimit,
    routing::{delete, get, post},
    Router,
};
use redis::aio::ConnectionManager;
use tower_http::{
    cors::{Any, CorsLayer},
    trace::TraceLayer,
};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use config::Config;

// ── Shared application state ─────────────────────────────────────────────────

#[derive(Clone)]
pub struct AppState {
    pub db: sqlx::SqlitePool,
    pub redis: ConnectionManager,
    pub config: Arc<Config>,
}

// ── Entry point ───────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Load .env (ignored if not present)
    let _ = dotenvy::dotenv();

    // Initialise structured logging – honours RUST_LOG env var
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".parse().unwrap()))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load config from environment
    let config = Config::from_env()?;
    let listen_addr = config.listen_addr.clone();

    // Connect to SQLite
    let db = db::create_pool(&config.database_url).await?;
    tracing::info!("connected to SQLite");

    // Connect to Redis
    let redis = cache::create_connection_manager(&config.redis_url).await?;
    tracing::info!("connected to Redis");

    let state = AppState {
        db,
        redis,
        config: Arc::new(config),
    };

    // ── Router ───────────────────────────────────────────────────────────────
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(handlers::health::live))
        .route("/ready", get(handlers::health::ready))
        // Public endpoints
        .route("/api/auth/signup", post(handlers::auth::signup))
        .route("/api/auth/login", post(handlers::auth::login))
        .route("/api/auth/logout", delete(handlers::auth::logout))
        // Called by the API gateway — protect with INTERNAL_EXCHANGE_SECRET when set
        .route(
            "/internal/token/exchange",
            post(handlers::auth::exchange_token),
        )
        .layer(DefaultBodyLimit::max(256 * 1024))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    // ── Listen ───────────────────────────────────────────────────────────────
    let listener = tokio::net::TcpListener::bind(&listen_addr).await?;
    tracing::info!(addr = %listen_addr, "auth-service listening");
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    Ok(())
}

async fn shutdown_signal() {
    let _ = tokio::signal::ctrl_c().await;
    tracing::info!("shutdown signal received, draining connections");
}

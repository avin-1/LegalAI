mod config;
mod middleware;
mod router;

use std::sync::Arc;

use axum::{
    extract::DefaultBodyLimit,
    http::StatusCode,
    middleware as axum_middleware,
    response::IntoResponse,
    routing::{any, get},
    Json, Router,
};
use reqwest::Client;
use serde_json::json;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use config::Config;
use middleware::phantom::phantom_swap;
use router::proxy;

// ── Shared application state ─────────────────────────────────────────────────

#[derive(Clone)]
pub struct AppState {
    /// Shared HTTP client for calling the Auth Service and downstream services.
    pub http: Client,
    pub config: Arc<Config>,
}

// ── Entry point ───────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _ = dotenvy::dotenv();

    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".parse().unwrap()))
        .with(tracing_subscriber::fmt::layer())
        .init();

    let config = Config::from_env()?;
    let listen_addr = config.listen_addr.clone();

    // Build a shared reqwest client (connection-pooled)
    let http = Client::builder()
        .timeout(std::time::Duration::from_secs(120))
        .build()?;

    let state = AppState {
        http,
        config: Arc::new(config),
    };

    // ── Router ───────────────────────────────────────────────────────────────
    //
    // All routes except `/health` and `/ready` first pass through `phantom_swap`:
    //   1. Extracts the opaque Bearer token.
    //   2. Calls /internal/token/exchange on the Auth Service.
    //   3. Injects the resulting JWT into the Authorization header.
    // Then the `proxy` handler forwards the mutated request downstream.
    //
    let app = Router::new()
        .route("/health", get(health_live))
        .route("/ready", get(health_ready))
        .route("/*path", any(proxy))
        .route_layer(axum_middleware::from_fn_with_state(
            state.clone(),
            phantom_swap,
        ))
        .layer(DefaultBodyLimit::max(10 * 1024 * 1024))
        .layer(config::build_cors_layer())
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&listen_addr).await?;
    tracing::info!(addr = %listen_addr, "api-gateway listening");
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    Ok(())
}

async fn health_live() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

async fn health_ready(axum::extract::State(state): axum::extract::State<AppState>) -> impl IntoResponse {
    let base = state.config.auth_service_url.trim_end_matches('/');
    let url = format!("{base}/ready");
    match state.http.get(&url).send().await {
        Ok(r) if r.status().is_success() => {
            (StatusCode::OK, Json(json!({ "status": "ready" }))).into_response()
        }
        Ok(r) => {
            tracing::warn!(status = %r.status(), url = %url, "auth service not ready");
            (
                StatusCode::SERVICE_UNAVAILABLE,
                Json(json!({ "status": "not_ready", "detail": "auth service /ready failed" })),
            )
                .into_response()
        }
        Err(e) => {
            tracing::warn!(error = %e, url = %url, "auth service /ready unreachable");
            (
                StatusCode::SERVICE_UNAVAILABLE,
                Json(json!({ "status": "not_ready", "detail": "auth service unreachable" })),
            )
                .into_response()
        }
    }
}

async fn shutdown_signal() {
    let _ = tokio::signal::ctrl_c().await;
    tracing::info!("shutdown signal received, draining connections");
}

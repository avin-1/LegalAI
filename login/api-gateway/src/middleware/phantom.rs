use axum::{
    body::Body,
    http::{HeaderValue, Request, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use reqwest::Client;
use serde_json::json;

use shared::models::{ExchangeRequest, ExchangeResponse};

use crate::AppState;

/// Tower / axum middleware that implements the **Phantom Token Swap**.
///
/// Public routes (`/api/auth/*`) are forwarded as-is without a token check.
/// For every other request:
/// 1. Extract the opaque `Bearer` token from `Authorization`.
/// 2. POST it to `{AUTH_SERVICE_URL}/internal/token/exchange`.
/// 3. Replace the original `Authorization` header with `Bearer <jwt>`.
/// 4. Pass the mutated request down the handler chain.
pub async fn phantom_swap(
    axum::extract::State(state): axum::extract::State<AppState>,
    mut req: Request<Body>,
    next: Next,
) -> Response {
    let path = req.uri().path();

    // ── Public routes: no Bearer → JWT swap ───────────────────────────────────
    if path.starts_with("/api/auth/")
        || path == "/health"
        || path == "/ready"
    {
        return next.run(req).await;
    }

    // ── 1. Extract the opaque token ──────────────────────────────────────────
    let opaque_token = match extract_bearer(req.headers()) {
        Some(t) => t,
        None => {
            return (
                StatusCode::UNAUTHORIZED,
                Json(json!({ "error": "missing Authorization Bearer header" })),
            )
                .into_response()
        }
    };

    // ── 2. Exchange with Auth Service ────────────────────────────────────────
    let jwt = match call_exchange(
        &state.http,
        &state.config.auth_service_url,
        state.config.internal_exchange_secret.as_deref(),
        &opaque_token,
    )
    .await
    {
        Ok(jwt) => jwt,
        Err(e) => {
            tracing::warn!(error = %e, "phantom-swap: token exchange failed");
            return (
                StatusCode::UNAUTHORIZED,
                Json(json!({ "error": "invalid or expired token" })),
            )
                .into_response();
        }
    };

    // ── 3. Replace Authorization header with the JWT ─────────────────────────
    let jwt_header = match HeaderValue::from_str(&format!("Bearer {jwt}")) {
        Ok(v) => v,
        Err(_) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({ "error": "internal error building auth header" })),
            )
                .into_response()
        }
    };

    req.headers_mut()
        .insert(axum::http::header::AUTHORIZATION, jwt_header);

    // ── 4. Forward to downstream handler ─────────────────────────────────────
    next.run(req).await
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn extract_bearer(headers: &axum::http::HeaderMap) -> Option<String> {
    headers
        .get(axum::http::header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
        .map(|t| t.to_owned())
}

async fn call_exchange(
    client: &Client,
    auth_service_url: &str,
    internal_secret: Option<&str>,
    opaque_token: &str,
) -> anyhow::Result<String> {
    let base = auth_service_url.trim_end_matches('/');
    let url = format!("{base}/internal/token/exchange");
    let body = ExchangeRequest {
        opaque_token: opaque_token.to_owned(),
    };

    let mut req = client.post(&url).json(&body);
    if let Some(secret) = internal_secret {
        req = req.header("x-internal-secret", secret);
    }

    let resp = req.send().await?.error_for_status()?;

    let exchange: ExchangeResponse = resp.json().await?;
    Ok(exchange.jwt)
}

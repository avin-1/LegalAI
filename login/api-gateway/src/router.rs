use axum::{
    body::Body,
    extract::State,
    http::{Request, StatusCode},
    response::{IntoResponse, Response},
    Json,
};
use reqwest::header::HeaderValue as ReqwestHeaderValue;
use serde_json::json;

use crate::AppState;

/// Path-based reverse-proxy handler.
///
/// Routes:
///   - `/api/auth/*` → Auth Service (same path and query)
///   - `/embed/*`    → EmbeddingAPI (strips `/embed` prefix) when configured
///   - `/graph/*`    → GraphAPI (strips `/graph` prefix) when configured
///
/// Receives the request *after* the phantom-swap middleware has replaced
/// the `Authorization` header with a valid JWT (except for `/api/auth/*`).
pub async fn proxy(State(state): State<AppState>, req: Request<Body>) -> Response {
    let path = req.uri().path();

    if path.starts_with("/api/auth/") {
        return forward_to_base(&state, &state.config.auth_service_url, req).await;
    }

    let (downstream_base, stripped_path) =
        if let Some(rest) = path.strip_prefix("/embed") {
            let Some(base) = state.config.embedding_api_url.as_deref() else {
                return (
                    StatusCode::NOT_IMPLEMENTED,
                    Json(json!({
                        "error": "Embedding proxy is not configured",
                        "hint": "Set EMBEDDING_API_URL to enable /embed/* routes."
                    })),
                )
                    .into_response();
            };
            (base, format!("{}{}", rest, query_string(req.uri())))
        } else if let Some(rest) = path.strip_prefix("/graph") {
            let Some(base) = state.config.graph_api_url.as_deref() else {
                return (
                    StatusCode::NOT_IMPLEMENTED,
                    Json(json!({
                        "error": "Graph proxy is not configured",
                        "hint": "Set GRAPH_API_URL to enable /graph/* routes."
                    })),
                )
                    .into_response();
            };
            (base, format!("{}{}", rest, query_string(req.uri())))
        } else if path == "/upload" || path == "/query" || path == "/explain" {
            let Some(base) = state.config.backend_url.as_deref() else {
                return (
                    StatusCode::NOT_IMPLEMENTED,
                    Json(json!({
                        "error": "Backend proxy is not configured",
                        "hint": "Set BACKEND_URL to enable /upload and /query routes."
                    })),
                )
                    .into_response();
            };
            (base, format!("{}{}", path, query_string(req.uri())))
        } else {
            return (
                StatusCode::NOT_FOUND,
                Json(json!({
                    "error": "unknown route",
                    "hint": "Use /api/auth/* for authentication, or /embed/* and /graph/* when those services are configured."
                })),
            )
                .into_response();
        };

    let stripped_path = normalize_stripped_path(&stripped_path);
    let downstream_url = format!("{downstream_base}{stripped_path}");

    forward_request(&state, &downstream_url, req).await
}

async fn forward_to_base(state: &AppState, base: &str, req: Request<Body>) -> Response {
    let path = req.uri().path();
    let q = query_string(req.uri());
    let downstream_url = format!("{base}{path}{q}");
    forward_request(state, &downstream_url, req).await
}

fn normalize_stripped_path(stripped_path: &str) -> String {
    if stripped_path.is_empty() || !stripped_path.starts_with('/') {
        format!("/{stripped_path}")
    } else {
        stripped_path.to_owned()
    }
}

async fn forward_request(state: &AppState, downstream_url: &str, req: Request<Body>) -> Response {
    let method = req.method().clone();
    let headers = req.headers().clone();

    let body_bytes = match axum::body::to_bytes(req.into_body(), usize::MAX).await {
        Ok(b) => b,
        Err(e) => {
            tracing::error!(error = %e, "failed to read request body");
            return (
                StatusCode::BAD_GATEWAY,
                Json(json!({ "error": "failed to read request body" })),
            )
                .into_response();
        }
    };

    let mut request_builder = state.http.request(
        reqwest::Method::from_bytes(method.as_str().as_bytes()).unwrap(),
        downstream_url,
    );

    for (name, value) in headers.iter() {
        if matches!(
            name.as_str(),
            "host" | "connection" | "transfer-encoding" | "te" | "trailer" | "upgrade"
        ) {
            continue;
        }
        if let Ok(val) = ReqwestHeaderValue::from_bytes(value.as_bytes()) {
            request_builder = request_builder.header(name.as_str(), val);
        }
    }

    match request_builder.body(body_bytes).send().await {
        Ok(resp) => {
            let status = StatusCode::from_u16(resp.status().as_u16())
                .unwrap_or(StatusCode::INTERNAL_SERVER_ERROR);
            let resp_headers = resp.headers().clone();
            let body_bytes = resp.bytes().await.unwrap_or_default();

            let mut response = Response::new(Body::from(body_bytes));
            *response.status_mut() = status;
            for (name, value) in resp_headers.iter() {
                if let Ok(n) = axum::http::header::HeaderName::from_bytes(name.as_str().as_bytes()) {
                    if let Ok(v) = axum::http::HeaderValue::from_bytes(value.as_bytes()) {
                        response.headers_mut().insert(n, v);
                    }
                }
            }
            response
        }
        Err(e) => {
            tracing::error!(error = %e, downstream_url = %downstream_url, "proxy request failed");
            (
                StatusCode::BAD_GATEWAY,
                Json(json!({ "error": "downstream service unavailable" })),
            )
                .into_response()
        }
    }
}

fn query_string(uri: &axum::http::Uri) -> String {
    uri.query()
        .map(|q| format!("?{q}"))
        .unwrap_or_default()
}

use axum::http::{HeaderValue, Method};
use tower_http::cors::{AllowOrigin, Any, CorsLayer};

/// Configuration for the API Gateway loaded from environment variables.
#[derive(Debug, Clone)]
pub struct Config {
    /// Address the gateway listens on.  Default: `0.0.0.0:3000`
    pub listen_addr: String,

    /// Base URL of the Auth Service (no trailing slash).
    /// Example: `http://localhost:3001`
    pub auth_service_url: String,

    /// Shared secret for `POST /internal/token/exchange` (optional but recommended).
    pub internal_exchange_secret: Option<String>,

    /// Base URL of the EmbeddingAPI microservice (no trailing slash), if proxying `/embed/*`.
    pub embedding_api_url: Option<String>,

    /// Base URL of the GraphAPI microservice (no trailing slash), if proxying `/graph/*`.
    pub graph_api_url: Option<String>,
    
    /// Base URL of the main Backend service (no trailing slash).
    pub backend_url: Option<String>,
}

impl Config {
    pub fn from_env() -> anyhow::Result<Self> {
        Ok(Self {
            listen_addr: std::env::var("LISTEN_ADDR")
                .unwrap_or_else(|_| "0.0.0.0:3000".into()),
            auth_service_url: trim_slash(required("AUTH_SERVICE_URL")?),
            internal_exchange_secret: std::env::var("INTERNAL_EXCHANGE_SECRET")
                .ok()
                .filter(|s| !s.is_empty()),
            embedding_api_url: optional_service_url("EMBEDDING_API_URL")?,
            graph_api_url: optional_service_url("GRAPH_API_URL")?,
            backend_url: optional_service_url("BACKEND_URL")?,
        })
    }
}

fn required(key: &str) -> anyhow::Result<String> {
    std::env::var(key)
        .map_err(|_| anyhow::anyhow!("required environment variable `{key}` is not set"))
}

fn optional_service_url(key: &str) -> anyhow::Result<Option<String>> {
    match std::env::var(key) {
        Ok(s) if s.trim().is_empty() => Ok(None),
        Ok(s) => Ok(Some(trim_slash(s))),
        Err(_) => Ok(None),
    }
}

fn trim_slash(mut s: String) -> String {
    while s.ends_with('/') {
        s.pop();
    }
    s
}

/// CORS: set `CORS_ALLOWED_ORIGINS` to a comma-separated list of exact origins
/// (for example `https://myapp.com,https://user-space.hf.space`). If unset or
/// empty, all origins are allowed (convenient for Hugging Face Spaces; tighten
/// for strict production browser clients).
pub fn build_cors_layer() -> CorsLayer {
    if let Ok(raw) = std::env::var("CORS_ALLOWED_ORIGINS") {
        let origins: Vec<HeaderValue> = raw
            .split(',')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .filter_map(|s| HeaderValue::from_str(s).ok())
            .collect();
        if !origins.is_empty() {
            return CorsLayer::new()
                .allow_origin(AllowOrigin::list(origins))
                .allow_methods([
                    Method::GET,
                    Method::POST,
                    Method::PUT,
                    Method::PATCH,
                    Method::DELETE,
                    Method::OPTIONS,
                ])
                .allow_headers(Any);
        }
    }

    CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any)
}

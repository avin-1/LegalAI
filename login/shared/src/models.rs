use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};


// ── Request / Response DTOs ─────────────────────────────────────────────────

/// Body sent by the client on login.
#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
}

/// Body returned to the client after a successful login.
#[derive(Debug, Serialize)]
pub struct LoginResponse {
    /// The opaque token the client must use in all subsequent requests.
    pub token: String,
    /// When the opaque token expires (UTC).
    pub expires_at: DateTime<Utc>,
}

/// Body sent by the API Gateway to the Auth Service for the phantom swap.
#[derive(Debug, Serialize, Deserialize)]
pub struct ExchangeRequest {
    pub opaque_token: String,
}

/// Body returned by the Auth Service to the API Gateway after a successful swap.
#[derive(Debug, Serialize, Deserialize)]
pub struct ExchangeResponse {
    /// Short-lived signed JWT for internal use.
    pub jwt: String,
}

// ── JWT Claims ───────────────────────────────────────────────────────────────

/// Claims embedded in every JWT issued by the Auth Service.
/// This is the struct that microservice middleware will extract.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserClaims {
    /// Subject — user UUID.
    pub sub: String,
    /// Username.
    pub username: String,
    /// Roles (e.g. ["admin", "user"]).
    pub roles: Vec<String>,
    /// Issued-at (Unix timestamp).
    pub iat: i64,
    /// Expiry (Unix timestamp).
    pub exp: i64,
}

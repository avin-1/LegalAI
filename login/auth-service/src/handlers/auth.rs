use argon2::{
    password_hash::{rand_core::OsRng, PasswordHasher, SaltString},
    Argon2, PasswordHash, PasswordVerifier,
};
use axum::{extract::State, http::HeaderMap, Json};
use chrono::{Duration, Utc};
use serde::Deserialize;
use serde_json::json;
use subtle::ConstantTimeEq;

use shared::{
    errors::AppError,
    models::{ExchangeRequest, ExchangeResponse, LoginRequest, LoginResponse},
};

use crate::{
    cache,
    db::{create_user, find_user_by_username},
    token::{generate_opaque_token, mint_jwt},
    AppState,
};

const USERNAME_MIN: usize = 3;
const USERNAME_MAX: usize = 32;
const PASSWORD_MIN: usize = 8;
const PASSWORD_MAX: usize = 256;

fn verify_internal_exchange(headers: &HeaderMap, expected: Option<&str>) -> Result<(), AppError> {
    let Some(exp) = expected else {
        return Ok(());
    };
    let got = headers
        .get("x-internal-secret")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    if got.len() != exp.len() {
        return Err(AppError::Forbidden);
    }
    if !bool::from(got.as_bytes().ct_eq(exp.as_bytes())) {
        return Err(AppError::Forbidden);
    }
    Ok(())
}

fn validate_username(username: &str) -> Result<(), AppError> {
    if username.len() < USERNAME_MIN || username.len() > USERNAME_MAX {
        return Err(AppError::BadRequest(format!(
            "username must be between {USERNAME_MIN} and {USERNAME_MAX} characters"
        )));
    }
    if !username
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '_')
    {
        return Err(AppError::BadRequest(
            "username may only contain letters, digits, and underscore".into(),
        ));
    }
    Ok(())
}

fn validate_signup_password(password: &str) -> Result<(), AppError> {
    if password.len() < PASSWORD_MIN || password.len() > PASSWORD_MAX {
        return Err(AppError::BadRequest(format!(
            "password must be between {PASSWORD_MIN} and {PASSWORD_MAX} characters"
        )));
    }
    Ok(())
}

/// Login accepts any non-empty password up to `PASSWORD_MAX` so we do not leak signup rules.
fn validate_login_password(password: &str) -> Result<(), AppError> {
    if password.is_empty() || password.len() > PASSWORD_MAX {
        return Err(AppError::InvalidCredentials);
    }
    Ok(())
}

fn normalize_username(username: &str) -> String {
    username.trim().to_lowercase()
}

// ── POST /api/auth/signup ────────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
pub struct SignupRequest {
    pub username: String,
    pub password: String,
}

/// Register a new user and immediately issue an opaque token (auto-login).
///
/// Steps:
/// 1. Hash the password with Argon2id.
/// 2. Insert the user into SQLite.
/// 3. Generate an opaque token, store it in Redis.
/// 4. Return the opaque token.
pub async fn signup(
    State(state): State<AppState>,
    Json(payload): Json<SignupRequest>,
) -> Result<Json<LoginResponse>, AppError> {
    let username = normalize_username(&payload.username);
    validate_username(&username)?;
    validate_signup_password(&payload.password)?;

    // 1. Check username is not already taken
    if find_user_by_username(&state.db, &username)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?
        .is_some()
    {
        return Err(AppError::Conflict("username already taken".into()));
    }

    // 2. Hash password
    let salt = SaltString::generate(&mut OsRng);
    let hash = Argon2::default()
        .hash_password(payload.password.as_bytes(), &salt)
        .map_err(|e| AppError::Internal(format!("password hashing failed: {e}")))?
        .to_string();

    // 3. Insert user
    let user_id = create_user(&state.db, &username, &hash)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    // 4. Issue opaque token (same as login)
    let opaque_token = generate_opaque_token();
    let claims_json = json!({
        "sub":      user_id.to_string(),
        "username": username,
        "roles":    ["user"],
    })
    .to_string();

    let mut redis = state.redis.clone();
    cache::set_token(
        &mut redis,
        &opaque_token,
        &claims_json,
        state.config.opaque_token_ttl_secs,
    )
    .await
    .map_err(|e| AppError::Internal(e.to_string()))?;

    let expires_at = Utc::now() + Duration::seconds(state.config.opaque_token_ttl_secs as i64);
    Ok(Json(LoginResponse {
        token: opaque_token,
        expires_at,
    }))
}

// ── POST /api/auth/login ─────────────────────────────────────────────────────

/// Authenticate a user and issue an opaque token.
pub async fn login(
    State(state): State<AppState>,
    Json(payload): Json<LoginRequest>,
) -> Result<Json<LoginResponse>, AppError> {
    let username = normalize_username(&payload.username);
    validate_username(&username)?;
    validate_login_password(&payload.password)?;

    // 1. Look up user
    let user = find_user_by_username(&state.db, &username)
        .await?
        .ok_or(AppError::InvalidCredentials)?;

    // 2. Verify Argon2 hash
    let parsed_hash = PasswordHash::new(&user.password_hash)
        .map_err(|_| AppError::Internal("malformed password hash in database".into()))?;

    Argon2::default()
        .verify_password(payload.password.as_bytes(), &parsed_hash)
        .map_err(|_| AppError::InvalidCredentials)?;

    // 3. Generate opaque token
    let opaque_token = generate_opaque_token();

    // 4. Cache claims
    let claims_json = json!({
        "sub":      user.id,
        "username": user.username,
        "roles":    user.roles,
    })
    .to_string();

    let mut redis = state.redis.clone();
    cache::set_token(
        &mut redis,
        &opaque_token,
        &claims_json,
        state.config.opaque_token_ttl_secs,
    )
    .await
    .map_err(|e| AppError::Internal(e.to_string()))?;

    // 5. Return opaque token
    let expires_at = Utc::now() + Duration::seconds(state.config.opaque_token_ttl_secs as i64);
    Ok(Json(LoginResponse {
        token: opaque_token,
        expires_at,
    }))
}

// ── POST /internal/token/exchange ───────────────────────────────────────────

/// Called exclusively by the API Gateway (not exposed publicly).
pub async fn exchange_token(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<ExchangeRequest>,
) -> Result<Json<ExchangeResponse>, AppError> {
    verify_internal_exchange(
        &headers,
        state.config.internal_exchange_secret.as_deref(),
    )?;

    let mut redis = state.redis.clone();
    let raw = cache::get_token(&mut redis, &payload.opaque_token)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?
        .ok_or(AppError::TokenNotFound)?;

    let claims: serde_json::Value =
        serde_json::from_str(&raw).map_err(|e| AppError::Internal(e.to_string()))?;

    let sub = claims["sub"].as_str().unwrap_or_default().to_owned();
    let username = claims["username"].as_str().unwrap_or_default().to_owned();
    let roles: Vec<String> = claims["roles"]
        .as_array()
        .map(|arr| {
            arr.iter()
                .filter_map(|r| r.as_str().map(str::to_owned))
                .collect()
        })
        .unwrap_or_default();

    let jwt = mint_jwt(&sub, &username, roles, &state.config.jwt_secret, state.config.jwt_expiry_secs)
        .map_err(|e| AppError::Internal(e.to_string()))?;

    tracing::info!(user = %username, "issued JWT via phantom-token exchange");

    Ok(Json(ExchangeResponse { jwt }))
}

// ── DELETE /api/auth/logout ──────────────────────────────────────────────────

/// Revoke an opaque token immediately.
pub async fn logout(
    State(state): State<AppState>,
    Json(payload): Json<ExchangeRequest>,
) -> Result<Json<serde_json::Value>, AppError> {
    let mut redis = state.redis.clone();
    cache::delete_token(&mut redis, &payload.opaque_token)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    Ok(Json(json!({ "message": "logged out successfully" })))
}


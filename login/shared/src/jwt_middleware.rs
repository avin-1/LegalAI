use axum::{
    async_trait,
    extract::FromRequestParts,
    http::{request::Parts, HeaderMap},
};
use jsonwebtoken::{decode, DecodingKey, Validation};

use crate::{errors::AppError, models::UserClaims};

/// A reusable axum extractor that any microservice can add to its handler
/// signature to authenticate requests.
///
/// # Usage
/// ```rust,ignore
/// async fn protected(
///     claims: UserClaims, // ← just add this parameter
///     // rest of your extractors …
/// ) -> impl IntoResponse { … }
/// ```
///
/// The middleware reads `JWT_SECRET` from the environment at call-time.
/// If the token is missing, expired, or tampered with the handler returns a
/// `401 Unauthorized` JSON error automatically.
#[async_trait]
impl<S> FromRequestParts<S> for UserClaims
where
    S: Send + Sync,
{
    type Rejection = AppError;

    async fn from_request_parts(parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
        let headers: &HeaderMap = &parts.headers;

        let bearer = headers
            .get(axum::http::header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.strip_prefix("Bearer "))
            .ok_or_else(|| AppError::Unauthorized("missing Bearer token".into()))?;

        let secret = std::env::var("JWT_SECRET")
            .map_err(|_| AppError::Internal("JWT_SECRET not set".into()))?;

        let token_data = decode::<UserClaims>(
            bearer,
            &DecodingKey::from_secret(secret.as_bytes()),
            &Validation::default(),
        )
        .map_err(|e| AppError::Unauthorized(format!("invalid JWT: {e}")))?;

        Ok(token_data.claims)
    }
}

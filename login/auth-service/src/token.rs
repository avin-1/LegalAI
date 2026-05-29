use chrono::Utc;
use jsonwebtoken::{encode, EncodingKey, Header};
use rand::RngCore;

use shared::models::UserClaims;

/// Generate a cryptographically secure 32-byte opaque token, hex-encoded.
/// The resulting string is 64 ASCII characters.
pub fn generate_opaque_token() -> String {
    let mut bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    hex::encode(bytes)
}

/// Mint a signed JWT for the given user claims.
///
/// # Arguments
/// * `sub`         – user UUID string
/// * `username`    – display username
/// * `roles`       – list of role strings (e.g. `["admin", "user"]`)
/// * `secret`      – HMAC-SHA256 signing secret (from `JWT_SECRET` env var)
/// * `expiry_secs` – token lifetime in seconds
pub fn mint_jwt(
    sub: &str,
    username: &str,
    roles: Vec<String>,
    secret: &str,
    expiry_secs: i64,
) -> Result<String, jsonwebtoken::errors::Error> {
    let now = Utc::now().timestamp();
    let claims = UserClaims {
        sub: sub.to_owned(),
        username: username.to_owned(),
        roles,
        iat: now,
        exp: now + expiry_secs,
    };

    encode(
        &Header::default(), // HS256
        &claims,
        &EncodingKey::from_secret(secret.as_bytes()),
    )
}

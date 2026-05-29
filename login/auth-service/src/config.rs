/// Configuration loaded from environment variables.
/// Call `Config::from_env()` at startup after loading `.env`.
#[derive(Debug, Clone)]
pub struct Config {
    /// Full SQLite connection URL.
    /// Example: `sqlite:auth.db` or `sqlite:///absolute/path.db`
    pub database_url: String,

    /// Full Redis connection URL.
    /// Example: `redis://127.0.0.1:6379` or `rediss://...` for TLS.
    pub redis_url: String,

    /// Secret used to sign/verify JWTs. At least 32 bytes (256 bits) recommended.
    pub jwt_secret: String,

    /// How long (in seconds) a JWT is valid.  Default: 300 (5 minutes).
    pub jwt_expiry_secs: i64,

    /// How long (in seconds) an opaque token is stored in Redis.  Default: 3600 (1 hour).
    pub opaque_token_ttl_secs: u64,

    /// Address the auth service listens on (`AUTH_LISTEN_ADDR`). Default: `0.0.0.0:3001`.
    /// Do not use `LISTEN_ADDR` here — on Hugging Face it is often set to `:7860` for the gateway.
    pub listen_addr: String,

    /// When set, `POST /internal/token/exchange` requires matching `x-internal-secret` header.
    /// The API gateway should set the same value.
    pub internal_exchange_secret: Option<String>,
}

impl Config {
    pub fn from_env() -> anyhow::Result<Self> {
        let jwt_secret = required("JWT_SECRET")?;
        if jwt_secret.len() < 32 {
            anyhow::bail!(
                "JWT_SECRET must be at least 32 characters (generate with: openssl rand -hex 32)"
            );
        }

        Ok(Self {
            database_url: required("DATABASE_URL")?,
            redis_url: required("REDIS_URL")?,
            jwt_secret,
            jwt_expiry_secs: std::env::var("JWT_EXPIRY_SECS")
                .unwrap_or_else(|_| "300".into())
                .parse()?,
            opaque_token_ttl_secs: std::env::var("OPAQUE_TOKEN_TTL_SECS")
                .unwrap_or_else(|_| "3600".into())
                .parse()?,
            // Do not use generic LISTEN_ADDR: Hugging Face users often set it to :7860 for the
            // gateway; the auth service must stay on an internal port (see start.sh).
            listen_addr: std::env::var("AUTH_LISTEN_ADDR")
                .unwrap_or_else(|_| "0.0.0.0:3001".into()),
            internal_exchange_secret: std::env::var("INTERNAL_EXCHANGE_SECRET")
                .ok()
                .filter(|s| !s.is_empty()),
        })
    }
}

fn required(key: &str) -> anyhow::Result<String> {
    std::env::var(key).map_err(|_| anyhow::anyhow!("required environment variable `{key}` is not set"))
}

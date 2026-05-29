use redis::{aio::ConnectionManager, AsyncCommands, Client};

/// Adjust `REDIS_URL` for TLS options. When `REDIS_TLS_INSECURE=1` (or `true` / `yes`),
/// append `#insecure` for `rediss://` (requires `tls-rustls-insecure` in the redis crate).
fn prepare_redis_url(redis_url: &str) -> anyhow::Result<String> {
    let mut url = redis_url.to_string();
    let insecure_env = matches!(
        std::env::var("REDIS_TLS_INSECURE").ok().as_deref(),
        Some("1") | Some("true") | Some("yes")
    );
    if insecure_env && url.starts_with("rediss://") {
        if url.contains("#insecure") {
            return Ok(url);
        }
        if url.contains('#') {
            anyhow::bail!(
                "REDIS_URL must not contain a `#` fragment (except `#insecure`) when using REDIS_TLS_INSECURE"
            );
        }
        url.push_str("#insecure");
    }
    Ok(url)
}

/// Create a Redis `ConnectionManager` (auto-reconnects on failure).
pub async fn create_connection_manager(redis_url: &str) -> anyhow::Result<ConnectionManager> {
    let url = prepare_redis_url(redis_url)?;
    let client = Client::open(url.as_str()).map_err(|e| {
        anyhow::anyhow!(
            "invalid REDIS_URL: {e}. For `rediss://` you need a TLS-enabled build; if you see TLS or certificate errors from Render, set secret REDIS_TLS_INSECURE=1 (disables cert verification — use only if needed)."
        )
    })?;
    let manager = ConnectionManager::new(client).await.map_err(|e| {
        anyhow::anyhow!(
            "Redis connection failed: {e}. \
             If the instance is on Render: in the Redis dashboard → Networking, allow external connections and add an inbound rule for Hugging Face (often `0.0.0.0/0` for testing). \
             For TLS errors, try secret REDIS_TLS_INSECURE=1."
        )
    })?;
    Ok(manager)
}

/// Store an opaque token → serialized payload mapping with a TTL.
pub async fn set_token(
    conn: &mut ConnectionManager,
    opaque_token: &str,
    payload: &str,
    ttl_secs: u64,
) -> anyhow::Result<()> {
    conn.set_ex::<_, _, ()>(opaque_token, payload, ttl_secs).await?;
    Ok(())
}

/// Retrieve the payload for an opaque token (returning `None` if not found / expired).
pub async fn get_token(
    conn: &mut ConnectionManager,
    opaque_token: &str,
) -> anyhow::Result<Option<String>> {
    let value: Option<String> = conn.get(opaque_token).await?;
    Ok(value)
}

/// Delete an opaque token (e.g., on logout).
pub async fn delete_token(
    conn: &mut ConnectionManager,
    opaque_token: &str,
) -> anyhow::Result<()> {
    conn.del::<_, ()>(opaque_token).await?;
    Ok(())
}

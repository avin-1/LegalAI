use axum::{extract::State, Json};
use serde_json::{json, Value};

use shared::errors::AppError;

use crate::AppState;

pub async fn live() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

pub async fn ready(State(state): State<AppState>) -> Result<Json<Value>, AppError> {
    sqlx::query_scalar::<_, i64>("SELECT 1")
        .fetch_one(&state.db)
        .await
        .map_err(|e| AppError::Internal(format!("database: {e}")))?;

    let mut redis = state.redis.clone();
    redis::cmd("PING")
        .query_async::<String>(&mut redis)
        .await
        .map_err(|e| AppError::Internal(format!("redis: {e}")))?;

    Ok(Json(json!({ "status": "ready" })))
}

use std::str::FromStr;

use sqlx::{
    sqlite::{SqliteConnectOptions, SqliteJournalMode, SqlitePoolOptions},
    SqlitePool,
};
use uuid::Uuid;

/// Row from the `users` table.
#[derive(Debug, sqlx::FromRow)]
pub struct UserRow {
    pub id: String,
    pub username: String,
    pub password_hash: String,
    /// Roles stored as a JSON string array, e.g. `["user"]`.
    pub roles: sqlx::types::Json<Vec<String>>,
}

/// Create and return a SQLite connection pool, running migrations automatically.
pub async fn create_pool(database_url: &str) -> anyhow::Result<SqlitePool> {
    // `Pool::connect(url)` does not enable `create_if_missing` by default; first boot then fails
    // with SQLITE_CANTOPEN (14) on some deployments. WAL can also fail on read-only / odd mounts,
    // so use DELETE journal for broader compatibility (e.g. Hugging Face Spaces).
    let options = SqliteConnectOptions::from_str(database_url)
        .map_err(|e| anyhow::anyhow!("invalid DATABASE_URL for SQLite: {e}"))?
        .create_if_missing(true)
        .journal_mode(SqliteJournalMode::Delete);

    let pool = SqlitePoolOptions::new()
        .max_connections(10)
        .connect_with(options)
        .await?;

    // Run embedded migrations from auth-service/migrations/
    sqlx::migrate!("./migrations").run(&pool).await?;

    Ok(pool)
}

/// Fetch a user row by username. Returns `None` when the user does not exist.
pub async fn find_user_by_username(
    pool: &SqlitePool,
    username: &str,
) -> Result<Option<UserRow>, sqlx::Error> {
    let row = sqlx::query_as::<_, UserRow>(
        "SELECT id, username, password_hash, roles FROM users WHERE username = ?",
    )
    .bind(username)
    .fetch_optional(pool)
    .await?;

    Ok(row)
}

/// Insert a new user into the database. Returns `Err` if the username is already taken.
pub async fn create_user(
    pool: &SqlitePool,
    username: &str,
    password_hash: &str,
) -> Result<Uuid, sqlx::Error> {
    let id = Uuid::new_v4();
    let roles_json = r#"["user"]"#;

    sqlx::query(
        "INSERT INTO users (id, username, password_hash, roles) VALUES (?, ?, ?, ?)",
    )
    .bind(id.to_string())
    .bind(username)
    .bind(password_hash)
    .bind(roles_json)
    .execute(pool)
    .await?;

    Ok(id)
}

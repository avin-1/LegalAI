-- SQLite migration — runs automatically via sqlx::migrate! at startup.

CREATE TABLE IF NOT EXISTS users (
    id            TEXT        PRIMARY KEY,
    username      TEXT        UNIQUE NOT NULL,
    password_hash TEXT        NOT NULL,  -- Argon2id hash produced by argon2 crate
    roles         TEXT        NOT NULL DEFAULT '["user"]' -- JSON string array
);

-- ── Example user (password = "secret") ───────────────────────────────────────
-- Generate a real hash with: cargo run --example hash_password "secret"
-- or use the argon2 CLI / any Argon2id library.
--
-- INSERT INTO users (username, password_hash, roles) VALUES
--   ('alice', '$argon2id$v=19$...', ARRAY['user']),
--   ('admin', '$argon2id$v=19$...', ARRAY['admin','user']);

@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
title Phantom Token Auth - Setup ^& Run

echo.
echo ============================================================
echo   Phantom Token Auth System - Setup ^& Launch
echo ============================================================
echo.

:: ── 1. Check Rust ────────────────────────────────────────────────────────────
where rustc >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Rust is not installed.
    echo   Install it from: https://rustup.rs/
    echo   Then re-run this script.
    pause
    exit /b 1
)
FOR /F "tokens=*" %%v IN ('rustc --version') DO SET RUST_VER=%%v
echo [OK] %RUST_VER%

:: ── 2. Check cargo ───────────────────────────────────────────────────────────
where cargo >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] cargo not found. Re-install Rust via rustup.
    pause
    exit /b 1
)

:: ── 3. Check PostgreSQL (psql) ────────────────────────────────────────────────
where psql >nul 2>&1
IF ERRORLEVEL 1 (
    echo [WARN] psql not found in PATH.
    echo   Make sure PostgreSQL is installed and its bin folder is in PATH.
    echo   Download: https://www.postgresql.org/download/windows/
    echo   Skipping automatic database setup...
    SET SKIP_DB=1
) ELSE (
    echo [OK] PostgreSQL (psql) found.
    SET SKIP_DB=0
)

:: ── 4. Check Redis ────────────────────────────────────────────────────────────
where redis-cli >nul 2>&1
IF ERRORLEVEL 1 (
    echo [WARN] redis-cli not found in PATH.
    echo   Memurai (Redis for Windows): https://www.memurai.com/
    echo   Or use WSL: wsl --install then install redis-server inside WSL.
    echo   Make sure Redis is running before starting the services.
) ELSE (
    echo [OK] redis-cli found.
)

echo.
echo ============================================================
echo   Step 1: Configure environment files
echo ============================================================

:: Auth Service .env
IF NOT EXIST "auth-service\.env" (
    echo Creating auth-service\.env from example...
    copy "auth-service\.env.example" "auth-service\.env" >nul
    echo.
    echo [ACTION REQUIRED] Edit auth-service\.env with your real values:
    echo   - DATABASE_URL  (PostgreSQL connection string)
    echo   - REDIS_URL     (Redis connection string)
    echo   - JWT_SECRET    (at least 32 random characters)
    echo.
    notepad "auth-service\.env"
) ELSE (
    echo [OK] auth-service\.env already exists.
)

:: API Gateway .env
IF NOT EXIST "api-gateway\.env" (
    echo Creating api-gateway\.env from example...
    copy "api-gateway\.env.example" "api-gateway\.env" >nul
    echo [OK] api-gateway\.env created (defaults should work for local dev).
) ELSE (
    echo [OK] api-gateway\.env already exists.
)

echo.
echo ============================================================
echo   Step 2: Set up PostgreSQL database
echo ============================================================

IF "!SKIP_DB!"=="0" (
    :: Parse DATABASE_URL from auth-service\.env to get DB name and host
    FOR /F "tokens=1,* delims==" %%a IN (auth-service\.env) DO (
        IF "%%a"=="DATABASE_URL" SET DB_URL=%%b
    )

    echo.
    SET /P SETUP_DB="Do you want to create the database and run the migration? (y/n): "
    IF /I "!SETUP_DB!"=="y" (
        echo.
        SET /P DB_USER="Enter your PostgreSQL superuser (default: postgres): "
        IF "!DB_USER!"=="" SET DB_USER=postgres
        SET /P DB_NAME="Enter the database name to create (default: auth_db): "
        IF "!DB_NAME!"=="" SET DB_NAME=auth_db
        SET /P DB_HOST="Enter the host (default: localhost): "
        IF "!DB_HOST!"=="" SET DB_HOST=localhost

        echo Creating database '!DB_NAME!'...
        psql -U !DB_USER! -h !DB_HOST! -c "CREATE DATABASE !DB_NAME!;" 2>nul
        IF ERRORLEVEL 1 (
            echo [WARN] Database may already exist — continuing.
        ) ELSE (
            echo [OK] Database '!DB_NAME!' created.
        )

        echo Running migration...
        psql -U !DB_USER! -h !DB_HOST! -d !DB_NAME! -f "auth-service\migrations\001_create_users.sql"
        IF ERRORLEVEL 1 (
            echo [ERROR] Migration failed. Check your credentials and try again.
        ) ELSE (
            echo [OK] Migration applied.
        )

        echo.
        echo To create a test user, run this in psql:
        echo   INSERT INTO users (username, password_hash, roles)
        echo   VALUES ('alice', '^<argon2id_hash^>', ARRAY['user']);
        echo.
        echo Generate an Argon2id hash with:
        echo   cargo run --example hash_password --manifest-path auth-service\Cargo.toml "your_password"
    )
) ELSE (
    echo [SKIP] PostgreSQL not found — set up your database manually then re-run.
)

echo.
echo ============================================================
echo   Step 3: Build the workspace (cargo check + build)
echo ============================================================
echo.
echo Running cargo build --workspace --release ...
echo (This will take a few minutes on first run while downloading crates)
echo.

cargo build --workspace --release
IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Build failed. Check the errors above and fix them.
    pause
    exit /b 1
)
echo.
echo [OK] Build successful.

echo.
echo ============================================================
echo   Step 4: Launch services
echo ============================================================
echo.
echo Starting auth-service on port 3001 in a new window...
start "Phantom Auth - Auth Service" cmd /k "cd /d %~dp0auth-service && cargo run --release --manifest-path ..\Cargo.toml --bin auth-service"

timeout /t 3 /nobreak >nul

echo Starting api-gateway on port 3000 in a new window...
start "Phantom Auth - API Gateway" cmd /k "cd /d %~dp0api-gateway && cargo run --release --manifest-path ..\Cargo.toml --bin api-gateway"

echo.
echo ============================================================
echo   All services launched!
echo ============================================================
echo.
echo   Auth Service  ->  http://localhost:3001
echo   API Gateway   ->  http://localhost:3000
echo.
echo   Quick test (PowerShell):
echo.
echo   # 1. Login
echo   $r = Invoke-RestMethod -Method Post -Uri http://localhost:3001/api/auth/login ^
echo        -ContentType 'application/json' ^
echo        -Body '{"username":"alice","password":"secret"}'
echo   $token = $r.token
echo.
echo   # 2. Call gateway with opaque token (phantom swap happens internally)
echo   Invoke-RestMethod -Uri http://localhost:3000/api/hello ^
echo        -Headers @{ Authorization = "Bearer $token" }
echo.
pause
ENDLOCAL

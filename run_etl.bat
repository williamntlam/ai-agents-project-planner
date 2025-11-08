@echo off
REM ETL Pipeline Runner Script for Windows
REM Automates the complete ETL pipeline execution from start to finish

setlocal enabledelayedexpansion

REM Script directory
cd /d "%~dp0"

REM Configuration
set ENV_FILE=.env
set DOCKER_COMPOSE_FILE=docker-compose.yml
set DB_SERVICE=pgvector
set ETL_SERVICE=etl_pipeline
set ETL_ENV=local

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--env" (
    set ETL_ENV=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help
shift
goto :parse_args

:end_parse

echo ========================================
echo ETL Pipeline Automation Script
echo ========================================
echo.

REM Check prerequisites
echo [1/5] Checking Prerequisites...

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)
echo [OK] Docker is installed

REM Check Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose is not installed.
        exit /b 1
    )
)
echo [OK] Docker Compose is available

REM Check .env file
if not exist "%ENV_FILE%" (
    echo [WARNING] .env file not found.
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [INFO] Created .env from .env.example
        echo [WARNING] Please edit .env file and add your OPENAI_API_KEY
        pause
    ) else (
        echo [ERROR] .env file not found and .env.example doesn't exist.
        exit /b 1
    )
)
echo [OK] .env file exists

REM Check data directory
if not exist "data" (
    echo [WARNING] data/ directory not found. Creating it...
    mkdir data\system_design 2>nul
    mkdir data\standards 2>nul
    echo [WARNING] Please add your markdown files to data/ directory
)
echo [OK] Data directory ready

REM Create logs directory
if not exist "logs" mkdir logs
echo [OK] Logs directory ready
echo.

REM Start database
echo [2/5] Starting Database...
docker-compose ps %DB_SERVICE% | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Starting PostgreSQL with pgvector...
    docker-compose up -d %DB_SERVICE%
    if errorlevel 1 (
        echo [ERROR] Failed to start database
        exit /b 1
    )
    
    echo [INFO] Waiting for database to be ready...
    set /a count=0
    :wait_db
    docker-compose exec -T %DB_SERVICE% pg_isready -U postgres >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Database is ready!
        goto :db_ready
    )
    timeout /t 2 /nobreak >nul
    set /a count+=2
    if !count! geq 60 (
        echo [ERROR] Database failed to start within 60 seconds
        docker-compose logs --tail=20 %DB_SERVICE%
        exit /b 1
    )
    goto :wait_db
) else (
    echo [INFO] Database is already running
)
:db_ready
echo.

REM Build ETL image
echo [3/5] Building ETL Pipeline Image...
docker-compose build %ETL_SERVICE%
if errorlevel 1 (
    echo [ERROR] Failed to build ETL pipeline image
    exit /b 1
)
echo [OK] ETL pipeline image built successfully
echo.

REM Run ETL pipeline
echo [4/5] Running ETL Pipeline...
echo [INFO] Using environment: %ETL_ENV%
set ETL_ENV=%ETL_ENV%
docker-compose run --rm %ETL_SERVICE% python -m etl_pipeline.main --env %ETL_ENV%
if errorlevel 1 (
    echo.
    echo [ERROR] ETL pipeline failed!
    exit /b 1
)
echo.
echo [OK] ETL pipeline completed successfully!
echo.

REM Show results
echo [5/5] Pipeline Results...
for /f "tokens=*" %%i in ('docker-compose exec -T %DB_SERVICE% psql -U postgres -d vector_db -t -c "SELECT COUNT(*) FROM document_chunks;" 2^>nul') do set CHUNK_COUNT=%%i
if defined CHUNK_COUNT (
    echo [OK] Loaded !CHUNK_COUNT! chunk(s) into vector database
) else (
    echo [WARNING] Could not retrieve chunk count from database
)
echo.

echo ========================================
echo Pipeline Execution Complete
echo ========================================
echo [SUCCESS] ETL pipeline finished successfully!
echo.
echo Next steps:
echo   - View logs: docker-compose logs %ETL_SERVICE%
echo   - Query database: docker-compose exec %DB_SERVICE% psql -U postgres -d vector_db
echo   - Stop database: docker-compose stop %DB_SERVICE%
echo.

exit /b 0

:show_help
echo Usage: run_etl.bat [OPTIONS]
echo.
echo Options:
echo   --env ENV    Environment to use (local, prod, staging) [default: local]
echo   --help, -h   Show this help message
echo.
exit /b 0


# Running ETL Pipeline with Docker

This guide explains how to run the ETL pipeline using Docker and Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- `.env` file configured with your API keys and database credentials

## Quick Start

### 1. Start the Database

```bash
# Start PostgreSQL with pgvector
docker-compose up -d pgvector

# Wait for database to be ready (check health status)
docker-compose ps
```

### 2. Run the ETL Pipeline

```bash
# Run the pipeline (will process and exit)
docker-compose up etl_pipeline

# Or run in detached mode
docker-compose up -d etl_pipeline

# View logs
docker-compose logs -f etl_pipeline
```

### 3. Stop Services

```bash
# Stop ETL pipeline (database keeps running)
docker-compose stop etl_pipeline

# Stop everything including database
docker-compose down

# Stop and remove volumes (⚠️ deletes database data)
docker-compose down -v
```

## Configuration

### Environment Variables

The pipeline uses environment variables from your `.env` file:

- `OPENAI_API_KEY` - Required for embeddings
- `DATABASE_URL` - Auto-configured to connect to pgvector container
- `ETL_ENV` - Environment name (local, prod, staging)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - Database credentials

### Running with Different Configs

```bash
# Use local config (default)
docker-compose run --rm etl_pipeline python -m etl_pipeline.main --env local

# Use production config
docker-compose run --rm etl_pipeline python -m etl_pipeline.main --env prod

# Use specific config file
docker-compose run --rm etl_pipeline python -m etl_pipeline.main --config /app/etl_pipeline/config/prod.yaml

# Dry run (test without loading)
docker-compose run --rm etl_pipeline python -m etl_pipeline.main --dry-run

# Verbose logging
docker-compose run --rm etl_pipeline python -m etl_pipeline.main --verbose
```

## Building the Image

```bash
# Build the ETL pipeline image
docker-compose build etl_pipeline

# Rebuild without cache
docker-compose build --no-cache etl_pipeline
```

## Data Persistence

- **Database**: Data persists in Docker volume `pgvector_data`
- **Logs**: Written to `./logs` directory (mounted as volume)
- **Data Files**: Read from `./data` directory (mounted as read-only)

## Troubleshooting

### Database Connection Issues

```bash
# Check if database is running
docker-compose ps pgvector

# Check database logs
docker-compose logs pgvector

# Test database connection
docker-compose exec pgvector psql -U postgres -d vector_db -c "SELECT version();"
```

### ETL Pipeline Issues

```bash
# View detailed logs
docker-compose logs -f etl_pipeline

# Run with verbose output
docker-compose run --rm etl_pipeline python -m etl_pipeline.main --verbose

# Check if data directory is mounted correctly
docker-compose exec etl_pipeline ls -la /app/data

# Check config files
docker-compose exec etl_pipeline ls -la /app/etl_pipeline/config
```

### Rebuild After Code Changes

```bash
# Rebuild and run
docker-compose build etl_pipeline
docker-compose up etl_pipeline
```

## Advanced Usage

### Custom Override File

Create `docker-compose.override.yml` to customize settings:

```yaml
version: '3.8'

services:
  etl_pipeline:
    command: ["python", "-m", "etl_pipeline.main", "--env", "prod"]
    environment:
      ETL_ENV: prod
```

### Running Multiple Times

The ETL pipeline runs once and exits. To run multiple times:

```bash
# Run again
docker-compose run --rm etl_pipeline

# Or restart the service
docker-compose restart etl_pipeline
```

### Accessing Container Shell

```bash
# Get shell access to container
docker-compose exec etl_pipeline /bin/bash

# Or run interactive command
docker-compose run --rm etl_pipeline /bin/bash
```

## Production Deployment

For production, consider:

1. **Use production config**: Set `ETL_ENV=prod` in `.env`
2. **Secure secrets**: Use Docker secrets or environment variables
3. **Resource limits**: Add resource constraints in docker-compose
4. **Health checks**: Monitor pipeline execution
5. **Scheduling**: Use cron or Kubernetes CronJob for regular runs

Example production override:

```yaml
services:
  etl_pipeline:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```


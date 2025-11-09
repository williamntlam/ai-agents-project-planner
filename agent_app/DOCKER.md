# Docker Setup for Agent Application

This guide explains how to run the agent application in Docker with the vector database.

## Prerequisites

1. Docker and Docker Compose installed
2. `.env` file in the project root with:
   - `POSTGRES_PASSWORD` (required)
   - `OPENAI_API_KEY` (required)
   - Optional: `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PORT`

## Quick Start

### 1. Build and Start Services

```bash
# From project root
docker-compose up -d pgvector
docker-compose build agent_app
docker-compose up -d agent_app
```

Or start everything at once:
```bash
docker-compose up -d
```

### 2. Run the Agent Application

#### Option A: Run via docker exec (Recommended)

```bash
docker exec -it agent_app python main.py \
  --brief "Build a REST API for a todo list application with user authentication" \
  --verbose
```

#### Option B: Override command in docker-compose.yml

Edit `docker-compose.yml` and uncomment/modify the command:
```yaml
agent_app:
  # ...
  command: ["python", "main.py", "--brief", "Your project brief", "--verbose"]
```

Then restart:
```bash
docker-compose restart agent_app
```

#### Option C: Run one-off container

```bash
docker-compose run --rm agent_app python main.py \
  --brief "Your project brief" \
  --config config/local.yaml \
  --output output/sdd.md \
  --verbose
```

## Services

### pgvector
- PostgreSQL database with pgvector extension
- Port: 5432 (configurable via `POSTGRES_PORT`)
- Data persisted in `pgvector_data` volume

### agent_app
- Agent application container
- Depends on `pgvector` service
- Mounts:
  - `./agent_app/config` → `/app/agent_app/config` (read-only)
  - `./output` → `/app/output` (read-write)
  - `./logs` → `/app/logs` (read-write)

## Environment Variables

Create a `.env` file in the project root:

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=vector_db
POSTGRES_PORT=5432

# OpenAI
OPENAI_API_KEY=sk-your-api-key-here
```

## Useful Commands

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agent_app
docker-compose logs -f pgvector
```

### Stop services
```bash
docker-compose stop
```

### Remove containers (keeps volumes)
```bash
docker-compose down
```

### Remove everything including volumes
```bash
docker-compose down -v
```

### Rebuild after code changes
```bash
docker-compose build agent_app
docker-compose up -d agent_app
```

### Access database
```bash
docker exec -it pgvector psql -U postgres -d vector_db
```

### Access agent_app shell
```bash
docker exec -it agent_app bash
```

## Troubleshooting

### Database connection errors
- Ensure `pgvector` service is healthy: `docker-compose ps`
- Check `DATABASE_URL` environment variable
- Verify database credentials in `.env`

### Import errors
- Ensure `PYTHONPATH=/app` is set
- Check that `etl_pipeline` is copied into container (needed for RAG tool)

### Permission errors
- Ensure output and logs directories exist and are writable
- Check volume mount permissions

## Development

For development, you may want to mount the source code as a volume:

```yaml
agent_app:
  volumes:
    # ... existing volumes ...
    - ./agent_app:/app/agent_app  # Mount source code for live editing
```

Then rebuild and restart:
```bash
docker-compose up -d agent_app
```


# Database Infrastructure

This directory contains Docker Compose configurations for shared databases used across the monorepo.

## pgvector (PostgreSQL with pgvector extension)

Vector database for RAG/semantic search.

### Usage

```bash
# Start the database
docker-compose -f databases/docker-compose.pgvector.yml up -d

# Stop the database
docker-compose -f databases/docker-compose.pgvector.yml down

# View logs
docker-compose -f databases/docker-compose.pgvector.yml logs -f
```

### Environment Variables

Set these in your `.env` file (see `.env.example` in the project root):

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here  # REQUIRED: Set a strong password
POSTGRES_DB=vector_db
POSTGRES_PORT=5432
```

**⚠️ Security Note:** The `POSTGRES_PASSWORD` environment variable is required and must be set. Do not use default passwords in production.

### Connection String

The connection string will be automatically constructed from your environment variables:
```
postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}
```


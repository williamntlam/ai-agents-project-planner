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

Set these in your `.env` file:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=vector_db
POSTGRES_PORT=5432
```

### Connection String

```
postgresql://postgres:postgres@localhost:5432/vector_db
```


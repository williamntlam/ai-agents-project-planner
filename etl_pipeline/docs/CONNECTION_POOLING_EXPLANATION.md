# Connection Pooling Explained

## What is Connection Pooling?

**Connection pooling** maintains a **pool of pre-established database connections** that can be reused across multiple database operations. It's NOT just one connection—it's a pool of multiple connections.

---

## The Problem: Creating Connections is Expensive

### Without Connection Pooling (Bad):

```python
# Every time you need the database...
def get_document(id):
    conn = psycopg2.connect("postgresql://...")  # ⏱️ Slow! 50-200ms
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = %s", (id,))
    result = cursor.fetchone()
    conn.close()  # Close connection
    return result

def get_document2(id):
    conn = psycopg2.connect("postgresql://...")  # ⏱️ Slow again! 50-200ms
    # ... same pattern
```

**Problems:**
- Creating a new connection takes **50-200ms** each time
- If you make 100 queries, that's **5-20 seconds** just for connections!
- Each connection consumes server resources
- Database has connection limits (typically 100-1000 connections)

---

## The Solution: Connection Pooling

### With Connection Pooling (Good):

```python
from psycopg2 import pool

# Create pool ONCE at startup
connection_pool = pool.SimpleConnectionPool(
    minconn=1,      # Minimum connections to keep alive
    maxconn=20,     # Maximum connections in pool
    dsn="postgresql://..."
)

# Reuse connections from pool (FAST!)
def get_document(id):
    conn = connection_pool.getconn()  # ⚡ Fast! <1ms (gets existing connection)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = %s", (id,))
        result = cursor.fetchone()
        return result
    finally:
        connection_pool.putconn(conn)  # Return connection to pool (reuse it!)

def get_document2(id):
    conn = connection_pool.getconn()  # ⚡ Fast! Reuses connection from pool
    # ... use it
    connection_pool.putconn(conn)  # Return to pool
```

**Benefits:**
- **Get connection:** <1ms (vs 50-200ms to create new)
- **Reuse connections:** Connections stay alive and get reused
- **Manage resources:** Pool limits total connections
- **100 queries:** Takes 0.1 seconds for connections (vs 5-20 seconds)

---

## How It Works

```
┌─────────────────────────────────────────┐
│      Connection Pool (Startup)          │
│                                         │
│  [Connection 1]  [Connection 2]        │
│  [Connection 3]  [Connection 4]          │
│                                         │
│  Pool Size: 4 connections (ready!)     │
└─────────────────────────────────────────┘
              ▲           │
              │           │
              │           │
        getconn()    putconn()
              │           │
              │           │
              ▼           ▼
    ┌─────────────────────────┐
    │   Your Application      │
    │                         │
    │   Query 1 → Get conn → Use → Return │
    │   Query 2 → Get conn → Use → Return │
    │   Query 3 → Get conn → Use → Return │
    └─────────────────────────┘
```

**Lifecycle:**
1. **Pool Creation** (at startup): Creates `minconn` connections (e.g., 5 connections)
2. **Get Connection** (when needed): Grabs an available connection from pool (<1ms)
3. **Use Connection**: Execute queries
4. **Return Connection**: Put it back in pool for reuse
5. **Scale Up**: If pool is empty, creates new connection (up to `maxconn`)

---

## Pool Configuration Explained

```python
connection_pool = pool.SimpleConnectionPool(
    minconn=5,      # Keep 5 connections always ready
    maxconn=20,     # Never exceed 20 connections total
    dsn="postgresql://..."
)
```

- **`minconn`**: Minimum connections to keep alive
  - If pool has 3 connections but `minconn=5`, it creates 2 more
  - Keeps connections ready even when idle
  
- **`maxconn`**: Maximum connections allowed
  - If 20 connections are in use, new requests must wait
  - Prevents overwhelming the database

**Example Sizing:**
- **Small app:** `minconn=2, maxconn=10`
- **Medium app:** `minconn=5, maxconn=20`
- **Large app:** `minconn=10, maxconn=50-100`

---

## Real-World Example: ETL Pipeline

### Without Pooling (Slow):
```python
# Process 1000 documents
for doc in documents:
    conn = psycopg2.connect("...")  # ⏱️ 100ms per document!
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chunks ...")
    conn.commit()
    conn.close()
# Total: 1000 × 100ms = 100 seconds just for connections!
```

### With Pooling (Fast):
```python
# Create pool once
pool = pool.SimpleConnectionPool(minconn=5, maxconn=20, dsn="...")

# Process 1000 documents
for doc in documents:
    conn = pool.getconn()  # ⚡ <1ms
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chunks ...")
    conn.commit()
    pool.putconn(conn)  # Return to pool
# Total: 1000 × 0.1ms = 0.1 seconds for connections!
```

---

## SQLAlchemy Also Has Built-in Pooling

If you're using SQLAlchemy (which you have in requirements.txt), it has **built-in connection pooling**:

```python
from sqlalchemy import create_engine

# SQLAlchemy automatically creates a connection pool!
engine = create_engine(
    "postgresql://...",
    pool_size=20,        # Equivalent to maxconn
    max_overflow=10,     # Extra connections if needed
    pool_pre_ping=True   # Verify connections before use
)

# Use it - pooling is automatic
with engine.connect() as conn:
    result = conn.execute("SELECT ...")
# Connection automatically returns to pool when done
```

**SQLAlchemy handles pooling automatically** - you don't need to manually get/put connections!

---

## When Do You Need It?

### You DON'T need pooling for:
- **Simple scripts** that run once
- **Low-frequency operations** (few queries)
- **Single-threaded applications** with sequential queries

### You DO need pooling for:
- **Production applications** (always!)
- **Web servers** handling multiple requests
- **ETL pipelines** processing many documents
- **Concurrent operations** (multiple threads/async tasks)
- **High-frequency queries**

---

## Common Mistakes

### ❌ Mistake 1: Creating Pool Inside Functions
```python
def bad_function():
    pool = pool.SimpleConnectionPool(...)  # WRONG! Creates pool every call
    conn = pool.getconn()
    # ...
```

**Fix:** Create pool once at application startup, reuse it everywhere.

### ❌ Mistake 2: Not Returning Connections
```python
def bad_function():
    conn = pool.getconn()
    # Use connection...
    # FORGOT to call pool.putconn(conn) - connection leaks!
```

**Fix:** Always use try/finally to ensure connections are returned:
```python
def good_function():
    conn = pool.getconn()
    try:
        # Use connection...
    finally:
        pool.putconn(conn)  # Always returns connection
```

### ❌ Mistake 3: Too Many Connections
```python
pool = pool.SimpleConnectionPool(minconn=100, maxconn=500)  # TOO MANY!
```

**Fix:** Start small, monitor database connection count, adjust as needed.

---

## Summary

| Aspect | Without Pooling | With Pooling |
|--------|----------------|--------------|
| **Connection Time** | 50-200ms per query | <1ms per query |
| **Resource Usage** | Creates/destroys connections constantly | Reuses connections |
| **Database Load** | High (many connection opens/closes) | Low (stable connections) |
| **Scalability** | Poor (hits connection limits quickly) | Good (manages connections efficiently) |

**Key Takeaway:** Connection pooling = **reuse pre-made connections** instead of creating new ones each time. It's like having a parking lot (pool) with reserved spots (connections) instead of finding new parking each time!


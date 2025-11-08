# Database Design Best Practices

## Database Selection

### Relational Databases (SQL)
**Use When:**
- ACID compliance is required
- Complex relationships between data
- Structured data with schema
- Need for transactions

**Examples:** PostgreSQL, MySQL, SQL Server

### NoSQL Databases

#### Document Stores
**Use When:**
- Flexible schema requirements
- JSON-like data structures
- Rapid development and iteration

**Examples:** MongoDB, CouchDB

#### Key-Value Stores
**Use When:**
- Simple data model
- High performance requirements
- Caching use cases

**Examples:** Redis, DynamoDB, Memcached

#### Column Stores
**Use When:**
- Analytics and data warehousing
- Time-series data
- Large-scale data processing

**Examples:** Cassandra, HBase

#### Graph Databases
**Use When:**
- Complex relationships
- Social networks
- Recommendation systems

**Examples:** Neo4j, Amazon Neptune

## Schema Design Principles

### Normalization
1. **First Normal Form (1NF)**: Eliminate duplicate columns
2. **Second Normal Form (2NF)**: Remove partial dependencies
3. **Third Normal Form (3NF)**: Remove transitive dependencies
4. **BCNF**: Boyce-Codd Normal Form for stricter rules

### Denormalization
- Trade-off between read performance and data consistency
- Use when read operations significantly outnumber writes
- Common in data warehousing and analytics

### Best Practices
1. **Primary Keys**: Use appropriate primary keys (UUIDs vs auto-increment)
2. **Foreign Keys**: Enforce referential integrity
3. **Indexes**: Create indexes on frequently queried columns
4. **Constraints**: Use constraints to maintain data integrity
5. **Naming Conventions**: Use consistent naming conventions

## Indexing Strategies

### Types of Indexes
- **B-Tree Indexes**: Default for most databases, good for range queries
- **Hash Indexes**: Fast equality lookups
- **Bitmap Indexes**: Good for low-cardinality columns
- **Full-Text Indexes**: For text search operations
- **Composite Indexes**: Multiple columns in one index

### Best Practices
1. **Index Selectivity**: Index highly selective columns
2. **Covering Indexes**: Include all queried columns in index
3. **Index Maintenance**: Monitor and remove unused indexes
4. **Partial Indexes**: Index subset of rows when appropriate
5. **Index Order**: Order columns in composite indexes by selectivity

## Query Optimization

### Best Practices
1. **Avoid SELECT ***: Select only needed columns
2. **Use EXPLAIN**: Analyze query execution plans
3. **Avoid N+1 Queries**: Use joins or batch loading
4. **Limit Results**: Use LIMIT for pagination
5. **Parameterized Queries**: Prevent SQL injection and enable query plan caching
6. **Connection Pooling**: Reuse database connections

### Common Anti-Patterns
- Missing indexes on WHERE clauses
- Functions on indexed columns in WHERE clauses
- Unnecessary joins
- Subqueries that can be replaced with joins
- Over-fetching data

## Transaction Management

### ACID Properties
- **Atomicity**: All or nothing
- **Consistency**: Database remains in valid state
- **Isolation**: Concurrent transactions don't interfere
- **Durability**: Committed changes persist

### Isolation Levels
1. **Read Uncommitted**: Lowest isolation, allows dirty reads
2. **Read Committed**: Prevents dirty reads
3. **Repeatable Read**: Prevents non-repeatable reads
4. **Serializable**: Highest isolation, prevents phantom reads

### Best Practices
1. **Keep Transactions Short**: Minimize lock duration
2. **Avoid Long-Running Transactions**: Can cause deadlocks
3. **Use Appropriate Isolation Levels**: Balance consistency and performance
4. **Handle Deadlocks**: Implement retry logic
5. **Optimistic vs Pessimistic Locking**: Choose based on contention

## Data Migration Strategies

### Best Practices
1. **Version Control**: Track schema changes in version control
2. **Backward Compatibility**: Maintain backward compatibility during migrations
3. **Rollback Plans**: Always have a rollback strategy
4. **Zero-Downtime Migrations**: Use techniques like blue-green deployment
5. **Data Validation**: Validate data after migration
6. **Testing**: Test migrations on staging environment first

## Backup and Recovery

### Backup Strategies
1. **Full Backups**: Complete database backup
2. **Incremental Backups**: Only changed data since last backup
3. **Differential Backups**: All changes since last full backup
4. **Point-in-Time Recovery**: Restore to specific timestamp

### Best Practices
1. **Regular Backups**: Schedule automated backups
2. **Test Restores**: Regularly test backup restoration
3. **Offsite Storage**: Store backups in different locations
4. **Retention Policy**: Define backup retention periods
5. **Encryption**: Encrypt backups for security


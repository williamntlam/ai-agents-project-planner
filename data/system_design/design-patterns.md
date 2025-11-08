# Design Patterns for System Design

## Creational Patterns

### Singleton Pattern
- Ensure only one instance of a class exists
- Use cases: Database connections, configuration managers, loggers
- Thread-safe implementation required in multi-threaded environments

### Factory Pattern
- Create objects without specifying exact class
- Abstract object creation
- Use cases: Creating different types of processors, validators

### Builder Pattern
- Construct complex objects step by step
- Fluent interface for object construction
- Use cases: Complex configuration objects, query builders

## Structural Patterns

### Adapter Pattern
- Allow incompatible interfaces to work together
- Wraps one interface to match another
- Use cases: Integrating third-party libraries, legacy system integration

### Decorator Pattern
- Add behavior to objects dynamically
- Compose objects at runtime
- Use cases: Adding features to core functionality, middleware

### Facade Pattern
- Provide simplified interface to complex subsystem
- Hide complexity behind simple interface
- Use cases: API gateways, service interfaces

### Proxy Pattern
- Provide placeholder for another object
- Control access to original object
- Use cases: Lazy loading, access control, caching

## Behavioral Patterns

### Observer Pattern
- Define one-to-many dependency between objects
- Notify dependents of state changes
- Use cases: Event systems, pub/sub, model-view updates

### Strategy Pattern
- Define family of algorithms, make them interchangeable
- Encapsulate algorithms in separate classes
- Use cases: Different sorting algorithms, payment methods, retry strategies

### Command Pattern
- Encapsulate requests as objects
- Parameterize clients with different requests
- Use cases: Undo/redo, queuing requests, logging requests

### Chain of Responsibility
- Pass request along chain of handlers
- Each handler decides to process or pass along
- Use cases: Middleware pipelines, validation chains, error handling

## Distributed System Patterns

### Service Discovery
- Services register and discover each other
- Dynamic service location
- Use cases: Microservices, container orchestration

### API Gateway
- Single entry point for all client requests
- Routes requests to appropriate services
- Use cases: Microservices architecture, API management

### Circuit Breaker
- Prevent cascading failures
- Open circuit when failures exceed threshold
- Use cases: External service calls, database connections

### Bulkhead
- Isolate resources to prevent cascading failures
- Separate thread pools, connection pools
- Use cases: Resource isolation, fault tolerance

### Saga Pattern
- Manage distributed transactions
- Sequence of local transactions with compensation
- Use cases: Distributed transactions, microservices

### CQRS (Command Query Responsibility Segregation)
- Separate read and write models
- Optimize each model independently
- Use cases: High-read or high-write systems, event sourcing

### Event Sourcing
- Store events as source of truth
- Rebuild state from events
- Use cases: Audit trails, time travel, complex domain models

## Data Patterns

### Repository Pattern
- Abstract data access layer
- Centralize data access logic
- Use cases: Database abstraction, testing, multiple data sources

### Unit of Work
- Track changes to objects
- Commit all changes together
- Use cases: Transaction management, change tracking

### Data Transfer Object (DTO)
- Transfer data between layers
- Simple data containers
- Use cases: API responses, service boundaries

### Active Record
- Object that contains data and behavior
- Direct database mapping
- Use cases: Simple CRUD operations, rapid prototyping

## Concurrency Patterns

### Producer-Consumer
- Separate production and consumption of work
- Use queues to decouple
- Use cases: Background processing, task queues

### Reader-Writer Lock
- Multiple readers or single writer
- Optimize for read-heavy workloads
- Use cases: Caching, configuration access

### Actor Model
- Entities that process messages asynchronously
- No shared state
- Use cases: Highly concurrent systems, Erlang, Akka

## Anti-Patterns to Avoid

### God Object
- Object that knows too much or does too much
- Violates single responsibility principle
- Solution: Break into smaller, focused objects

### Spaghetti Code
- Unstructured, tangled code
- Hard to understand and maintain
- Solution: Apply design patterns, refactor

### Premature Optimization
- Optimizing before measuring
- Can make code more complex
- Solution: Profile first, optimize bottlenecks

### Copy-Paste Programming
- Duplicating code instead of reusing
- Maintenance nightmare
- Solution: Extract common functionality

### Magic Numbers
- Hard-coded numbers without explanation
- Hard to understand and maintain
- Solution: Use named constants

## Pattern Selection Guidelines

### Consider Context
- Understand problem domain
- Consider system constraints
- Evaluate trade-offs

### Start Simple
- Don't over-engineer
- Add complexity when needed
- YAGNI (You Aren't Gonna Need It)

### Maintainability
- Code should be readable
- Easy to test
- Easy to modify

### Performance
- Consider performance implications
- Measure before optimizing
- Balance with maintainability


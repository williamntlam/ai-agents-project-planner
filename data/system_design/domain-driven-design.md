# Domain-Driven Design Patterns

## Overview
Domain-Driven Design (DDD) is an approach to software development that centers the development on programming a domain model that has a rich understanding of the processes and rules of a domain.

## Strategic Design Patterns

### Bounded Context
**Definition**: A boundary within which a particular domain model is valid and applicable.

**Purpose**:
- Explicitly define model boundaries
- Prevent model confusion
- Allow different models for same concept
- Organize large applications

**Characteristics**:
- Has its own ubiquitous language
- Own domain model
- Own database (potentially)
- Own team (ideally)

**Best Practices**:
1. Identify natural boundaries
2. Keep contexts focused
3. Define context mapping
4. Document context boundaries
5. Evolve boundaries as needed

### Ubiquitous Language
**Definition**: A language structured around the domain model and used by all team members to connect all activities of the team with the software.

**Purpose**:
- Shared understanding
- Communication tool
- Reduces translation errors
- Aligns code with domain

**Characteristics**:
- Used in code
- Used in conversations
- Used in documentation
- Evolves with domain

**Best Practices**:
1. Use domain terms in code
2. Avoid technical jargon in domain
3. Evolve language with domain
4. Document language explicitly
5. Review language regularly

### Context Mapping
**Definition**: A technique to visualize and document relationships between bounded contexts.

**Relationship Types**:
- **Shared Kernel**: Shared subset of model
- **Customer-Supplier**: Upstream/downstream relationship
- **Conformist**: Downstream conforms to upstream
- **Anticorruption Layer**: Translates between contexts
- **Separate Ways**: Independent development
- **Open Host Service**: Published language for integration
- **Partnership**: Mutual dependency

**Best Practices**:
1. Map all context relationships
2. Identify integration points
3. Plan integration strategies
4. Document relationships
5. Review mappings regularly

## Tactical Design Patterns

### Entity
**Definition**: An object that is not defined by its attributes, but rather by a thread of continuity and its identity.

**Characteristics**:
- Has unique identity
- Identity persists over time
- Can change attributes
- Lifecycle is important

**Use Cases**:
- Objects with identity
- Objects that change over time
- Objects with lifecycle
- Domain objects with identity

**Best Practices**:
1. Use meaningful identity
2. Protect identity
3. Keep identity stable
4. Don't use identity for equality when inappropriate
5. Consider value objects first

### Value Object
**Definition**: An object that describes some characteristic or attribute but has no conceptual identity.

**Characteristics**:
- Defined by attributes
- Immutable
- Equality by value
- No identity

**Use Cases**:
- Describing characteristics
- Measurements
- Money, addresses
- Immutable concepts

**Benefits**:
- Immutability
- Simpler equality
- Can be shared
- Thread-safe

**Best Practices**:
1. Make immutable
2. Validate on creation
3. Use for descriptive concepts
4. Don't use for entities
5. Consider performance for large objects

### Aggregate
**Definition**: A cluster of associated objects that are treated as a unit for the purpose of data changes.

**Structure**:
- **Aggregate Root**: Single entry point
- **Entities**: Within aggregate
- **Value Objects**: Within aggregate
- **Invariants**: Consistency rules

**Rules**:
- Only aggregate root has global identity
- External references only to root
- Objects within can reference each other
- Invariants enforced within aggregate
- Transactions modify one aggregate

**Best Practices**:
1. Keep aggregates small
2. Enforce invariants
3. Use aggregate root as entry point
4. Design for consistency
5. Consider performance

### Domain Service
**Definition**: An operation that doesn't conceptually belong to any entity or value object.

**Characteristics**:
- Stateless operation
- Domain concept
- Not naturally part of entity
- Expressed in ubiquitous language

**Use Cases**:
- Operations spanning multiple entities
- Complex domain calculations
- Domain logic not fitting entities
- Stateless domain operations

**Best Practices**:
1. Keep stateless
2. Express in domain language
3. Don't create for simple operations
4. Keep focused
5. Consider if should be entity method

### Repository
**Definition**: A mechanism for encapsulating storage, retrieval, and search behavior which emulates a collection of objects.

**Purpose**:
- Abstract persistence
- Collection-like interface
- Domain-focused queries
- Testability

**Characteristics**:
- Collection metaphor
- Domain language queries
- Hides persistence
- Per aggregate root

**Best Practices**:
1. One repository per aggregate root
2. Use domain language
3. Hide persistence details
4. Keep simple
5. Consider specification pattern

### Factory
**Definition**: Encapsulates the logic of creating complex objects and aggregates.

**Purpose**:
- Encapsulate creation logic
- Ensure valid objects
- Hide construction complexity
- Express creation in domain language

**Use Cases**:
- Complex object creation
- Aggregate creation
- Ensuring invariants
- Multiple construction paths

**Best Practices**:
1. Use for complex creation
2. Ensure invariants
3. Use domain language
4. Keep focused
5. Consider builder pattern

### Specification
**Definition**: Encapsulates a business rule that is a boolean predicate.

**Purpose**:
- Reusable business rules
- Composable rules
- Testable rules
- Domain language expression

**Structure**:
- IsSatisfiedBy method
- Composable (AND, OR, NOT)
- Can be used for selection
- Can be used for validation

**Use Cases**:
- Complex queries
- Business rule validation
- Selection criteria
- Composable rules

**Best Practices**:
1. Keep focused on single rule
2. Make composable
3. Use domain language
4. Keep stateless
5. Consider performance

## Application Patterns

### Application Service
**Definition**: Defines the jobs the software should do and directs the expressive domain objects to work out problems.

**Purpose**:
- Coordinate domain objects
- Transaction boundaries
- Use case implementation
- Application entry point

**Characteristics**:
- Thin layer
- Coordinates domain
- Transaction management
- No business logic

**Best Practices**:
1. Keep thin
2. Coordinate, don't implement
3. Manage transactions
4. One method per use case
5. Don't put business logic here

### Domain Event
**Definition**: Something that happened in the domain that domain experts care about.

**Purpose**:
- Communicate domain occurrences
- Decouple components
- Enable event sourcing
- Audit trail

**Characteristics**:
- Past tense naming
- Immutable
- Contains relevant data
- Timestamp

**Use Cases**:
- Important domain occurrences
- Decoupling
- Event sourcing
- Integration

**Best Practices**:
1. Use past tense
2. Make immutable
3. Include relevant data
4. Keep focused
5. Consider event sourcing

### Event Sourcing
**Definition**: Store all changes to application state as a sequence of events.

**Purpose**:
- Complete audit trail
- Time travel
- Replay events
- Event-driven architecture

**Benefits**:
- Complete history
- Debugging
- Analytics
- Flexibility

**Challenges**:
- Event versioning
- Snapshot management
- Query complexity
- Eventual consistency

**Best Practices**:
1. Use for important domains
2. Plan for event versioning
3. Consider snapshots
4. Handle eventual consistency
5. Document event schema

## Integration Patterns

### Anti-Corruption Layer
**Definition**: An isolating layer that provides clients with functionality in terms of their own domain model.

**Purpose**:
- Protect domain model
- Translate between models
- Isolate legacy systems
- Maintain model integrity

**Structure**:
- Facade to legacy system
- Adapters for translation
- Translators between models
- Isolates domain

**Best Practices**:
1. Keep translation logic here
2. Don't leak legacy concepts
3. Maintain domain integrity
4. Document translations
5. Consider performance

### Published Language
**Definition**: A well-documented shared language used for communication between bounded contexts.

**Purpose**:
- Standard integration format
- Reduce translation
- Version management
- Clear contracts

**Characteristics**:
- Well documented
- Versioned
- Stable
- Shared

**Best Practices**:
1. Document thoroughly
2. Version carefully
3. Keep stable
4. Evolve carefully
5. Communicate changes

## Implementation Guidelines

### Layered Architecture
**Layers**:
- **User Interface**: Presentation
- **Application**: Use cases, coordination
- **Domain**: Business logic
- **Infrastructure**: Technical concerns

**Principles**:
- Dependencies point inward
- Domain has no dependencies
- Infrastructure implements interfaces
- Application coordinates

### Hexagonal Architecture (Ports and Adapters)
**Structure**:
- **Core**: Domain and application
- **Ports**: Interfaces
- **Adapters**: Implementations

**Benefits**:
- Isolates core
- Testable
- Flexible
- Technology independent

### CQRS (Command Query Responsibility Segregation)
**Purpose**:
- Separate read and write models
- Optimize independently
- Scale reads and writes separately
- Support event sourcing

**When to Use**:
- Different read/write requirements
- High read or write load
- Complex domain
- Event sourcing

## Best Practices

1. **Start with Domain**: Focus on domain first
2. **Ubiquitous Language**: Use domain language everywhere
3. **Bounded Contexts**: Define clear boundaries
4. **Aggregates**: Design small, focused aggregates
5. **Events**: Use events for important occurrences
6. **Refactor**: Continuously refine model
7. **Collaborate**: Work with domain experts
8. **Document**: Document model and decisions

## Common Mistakes

1. **Anemic Domain Model**: Logic in services, not domain
2. **God Aggregates**: Aggregates too large
3. **Leaky Abstractions**: Technical concerns in domain
4. **Over-Engineering**: Too many patterns
5. **Ignoring Context**: Not defining bounded contexts
6. **Technical Language**: Using technical terms in domain


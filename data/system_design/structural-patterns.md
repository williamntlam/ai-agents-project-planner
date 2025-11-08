# Structural Design Patterns

## Overview
Structural patterns explain how to assemble objects and classes into larger structures while keeping these structures flexible and efficient. They focus on relationships between entities.

## Adapter Pattern

### Intent
Allow objects with incompatible interfaces to collaborate by wrapping an object with an adapter that makes it compatible with another class.

### Structure
- **Target**: Interface expected by client
- **Adaptee**: Existing class with incompatible interface
- **Adapter**: Wraps adaptee and implements target interface

### Types
- **Object Adapter**: Uses composition (wraps adaptee)
- **Class Adapter**: Uses inheritance (extends adaptee)

### Use Cases
- Integrating third-party libraries
- Legacy system integration
- API version compatibility
- Interface standardization
- Wrapper for external services

### Benefits
- Enables collaboration between incompatible interfaces
- Single Responsibility Principle
- Open/Closed Principle
- Reuses existing functionality

### Best Practices
1. Use when integrating incompatible interfaces
2. Prefer composition over inheritance (Object Adapter)
3. Keep adapter focused on adaptation
4. Don't add business logic to adapter
5. Consider interface design to avoid need for adapters

## Bridge Pattern

### Intent
Split a large class or set of closely related classes into two separate hierarchies—abstraction and implementation—which can be developed independently.

### Structure
- **Abstraction**: High-level control layer
- **Implementation**: Low-level platform details
- **Refined Abstraction**: Extends abstraction
- **Concrete Implementation**: Implements implementation interface

### Use Cases
- Platform-independent code
- UI frameworks (different platforms)
- Database drivers
- Device drivers
- Plugin architectures

### Benefits
- Separates abstraction from implementation
- Platform independence
- Hides implementation details
- Can change implementations at runtime

### Best Practices
1. Use when you want to avoid permanent binding
2. Use when both abstractions and implementations should be extensible
3. Hide implementation details from clients
4. Reduce coupling between abstraction and implementation

## Composite Pattern

### Intent
Compose objects into tree structures to represent part-whole hierarchies. Lets clients treat individual objects and compositions uniformly.

### Structure
- **Component**: Base interface for all objects
- **Leaf**: Represents leaf objects (no children)
- **Composite**: Stores child components and implements child operations

### Use Cases
- File system representation
- UI component trees
- Organizational structures
- Expression trees
- Menu systems

### Benefits
- Uniform treatment of individual and composite objects
- Easy to add new component types
- Simplifies client code
- Flexible structure

### Best Practices
1. Use when you have tree structures
2. Clients should treat all objects uniformly
3. Keep component interface simple
4. Consider performance for deep trees
5. Handle leaf vs composite differences carefully

## Decorator Pattern

### Intent
Attach additional responsibilities to objects dynamically. Provides flexible alternative to subclassing for extending functionality.

### Structure
- **Component**: Interface for objects that can have responsibilities added
- **Concrete Component**: Defines object to which responsibilities can be added
- **Decorator**: Maintains reference to component and defines interface matching component
- **Concrete Decorator**: Adds responsibilities to component

### Use Cases
- Adding features to core functionality
- Middleware in web frameworks
- Stream processing
- UI component enhancement
- Input/output streams

### Benefits
- More flexible than inheritance
- Responsibilities can be added/removed at runtime
- Mix and match features
- Single Responsibility Principle
- Open/Closed Principle

### Best Practices
1. Use when you need to add responsibilities dynamically
2. Use when subclassing would be impractical
3. Keep decorators focused on single responsibility
4. Maintain decorator order when it matters
5. Consider performance overhead

## Facade Pattern

### Intent
Provide a unified interface to a set of interfaces in a subsystem. Defines a higher-level interface that makes the subsystem easier to use.

### Structure
- **Facade**: Provides simple interface to complex subsystem
- **Subsystem Classes**: Implement subsystem functionality
- **Client**: Uses facade instead of subsystem directly

### Use Cases
- Simplifying complex APIs
- API gateways
- Service interfaces
- Library wrappers
- Legacy system integration

### Benefits
- Simplifies complex subsystems
- Reduces coupling
- Provides convenient interface
- Hides subsystem complexity
- Makes subsystem easier to use

### Best Practices
1. Use to simplify complex subsystems
2. Don't add business logic to facade
3. Keep facade focused on simplification
4. Can have multiple facades for different use cases
5. Document what facade does and doesn't do

## Flyweight Pattern

### Intent
Use sharing to support large numbers of fine-grained objects efficiently. Reduces memory usage by sharing intrinsic state.

### Structure
- **Flyweight**: Interface for flyweight objects
- **Concrete Flyweight**: Implements flyweight interface, stores intrinsic state
- **Flyweight Factory**: Creates and manages flyweight objects
- **Client**: Maintains extrinsic state

### Use Cases
- Text editors (character objects)
- Game development (particle systems)
- GUI applications (icon objects)
- Large numbers of similar objects
- Memory-constrained environments

### Benefits
- Reduces memory usage
- Improves performance
- Shares common state
- Useful for large object counts

### Best Practices
1. Use when large numbers of similar objects
2. Separate intrinsic and extrinsic state
3. Ensure flyweights are immutable
4. Use factory to manage flyweights
5. Consider thread safety

## Proxy Pattern

### Intent
Provide a surrogate or placeholder for another object to control access to it. Adds a level of indirection.

### Types
- **Virtual Proxy**: Lazy initialization of expensive objects
- **Protection Proxy**: Controls access to original object
- **Remote Proxy**: Represents object in different address space
- **Smart Reference**: Additional actions when object is accessed

### Use Cases
- Lazy loading
- Access control
- Caching
- Remote object access
- Logging and monitoring

### Benefits
- Controls access to original object
- Lazy initialization
- Can add additional functionality
- Can hide complexity of remote objects

### Best Practices
1. Use when you need to control object access
2. Keep proxy interface same as subject
3. Use for lazy loading when appropriate
4. Consider performance implications
5. Document proxy behavior clearly

## Pattern Selection Guide

### When to Use Adapter
- Need to use incompatible interface
- Integrating third-party code
- Legacy system integration

### When to Use Bridge
- Want to avoid permanent binding
- Both abstraction and implementation should be extensible
- Platform independence needed

### When to Use Composite
- Represent part-whole hierarchies
- Clients should treat all objects uniformly
- Tree structures

### When to Use Decorator
- Add responsibilities dynamically
- Subclassing would be impractical
- Need to mix and match features

### When to Use Facade
- Simplify complex subsystem
- Provide convenient interface
- Reduce coupling

### When to Use Flyweight
- Large numbers of similar objects
- Memory is constrained
- Intrinsic state can be shared

### When to Use Proxy
- Need to control access
- Lazy loading required
- Remote object access
- Additional functionality needed

## Common Mistakes

### Adapter Overuse
- Creating adapters when refactoring would be better
- Adding business logic to adapters
- Not considering interface design

### Composite Complexity
- Making component interface too complex
- Not handling leaf vs composite properly
- Performance issues with deep trees

### Decorator Overhead
- Too many decorators affecting performance
- Not maintaining decorator order
- Adding business logic to decorators

### Facade Misuse
- Adding business logic to facade
- Creating god object facade
- Not documenting facade limitations

### Proxy Overhead
- Unnecessary proxy layers
- Not considering performance impact
- Complex proxy logic

## Performance Considerations

### Adapter
- Minimal overhead
- Usually just method forwarding

### Bridge
- No runtime overhead
- Compile-time abstraction

### Composite
- Tree traversal can be expensive
- Consider caching for deep trees

### Decorator
- Chain of decorators adds overhead
- Consider for high-performance scenarios

### Facade
- Minimal overhead
- May add method call layer

### Flyweight
- Significant memory savings
- Lookup overhead in factory

### Proxy
- Overhead depends on proxy type
- Virtual proxy saves initialization cost
- Protection proxy adds access check overhead


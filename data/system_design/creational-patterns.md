# Creational Design Patterns

## Overview
Creational patterns provide object creation mechanisms that increase flexibility and reuse of existing code. They abstract the instantiation process and help make a system independent of how its objects are created, composed, and represented.

## Singleton Pattern

### Intent
Ensure a class has only one instance and provide a global point of access to it.

### Structure
- Single instance shared across application
- Private constructor prevents direct instantiation
- Static method provides access to instance
- Lazy or eager initialization

### Use Cases
- Database connection pools
- Configuration managers
- Logging systems
- Caching systems
- Thread pools

### Implementation Considerations
- **Thread Safety**: Critical in multi-threaded environments
- **Lazy vs Eager**: Choose based on initialization cost
- **Double-Checked Locking**: For thread-safe lazy initialization
- **Enum Singleton**: Simplest thread-safe implementation in Java

### Best Practices
1. Use when exactly one instance is needed
2. Ensure thread safety
3. Consider dependency injection as alternative
4. Be cautious of global state issues
5. Test singleton behavior carefully

### Anti-Patterns
- Overuse leading to tight coupling
- Making everything a singleton
- Using singleton for stateless utilities

## Factory Pattern

### Intent
Create objects without specifying the exact class of object that will be created.

### Simple Factory
- Single factory class creates different types
- Client doesn't know concrete classes
- Simple but violates Open/Closed Principle

### Factory Method Pattern
- Abstract method for object creation
- Subclasses decide which class to instantiate
- Follows Open/Closed Principle
- More flexible than Simple Factory

### Abstract Factory Pattern
- Interface for creating families of related objects
- Multiple factory methods
- Creates objects that work together
- Ensures compatibility between objects

### Use Cases
- Creating different types of processors
- Building different UI components
- Creating database connections
- Payment method selection
- Document parsers

### Best Practices
1. Use when object creation logic is complex
2. Use when you want to decouple creation from usage
3. Abstract Factory for families of related objects
4. Factory Method for single product hierarchies
5. Consider dependency injection frameworks

## Builder Pattern

### Intent
Construct complex objects step by step. Allows construction of objects using a fluent interface.

### Structure
- Builder class with setter methods
- Build method that returns final object
- Director (optional) that orchestrates building
- Can create different representations

### Use Cases
- Complex configuration objects
- SQL query builders
- HTTP request builders
- Object construction with many optional parameters
- Immutable object construction

### Benefits
- Clear, readable object construction
- Handles optional parameters elegantly
- Can validate before construction
- Supports immutable objects
- Fluent interface improves readability

### Best Practices
1. Use for objects with many constructor parameters
2. Use when construction steps are complex
3. Consider immutability
4. Validate in build method
5. Make builder methods chainable

### Example Scenarios
- Configuration objects with many optional fields
- Database query construction
- API request building
- Test data builders

## Prototype Pattern

### Intent
Specify the kinds of objects to create using a prototypical instance, and create new objects by copying this prototype.

### Structure
- Prototype interface with clone method
- Concrete prototypes implement cloning
- Client creates objects by cloning
- Shallow vs deep copy considerations

### Use Cases
- Objects expensive to create
- Avoiding subclass proliferation
- Runtime object creation
- Configuration templates
- Game object spawning

### Implementation Types
- **Shallow Copy**: Copies object references
- **Deep Copy**: Creates new instances of referenced objects
- **Serialization-Based**: Clone via serialization

### Best Practices
1. Use when object creation is expensive
2. Use when classes vary only in configuration
3. Implement proper cloning (shallow vs deep)
4. Consider copy constructors
5. Handle circular references

## Object Pool Pattern

### Intent
Reuse objects that are expensive to create by maintaining a pool of initialized objects ready to use.

### Structure
- Pool manager maintains collection
- Objects are checked out and returned
- Pre-initialized objects for reuse
- Limits maximum pool size

### Use Cases
- Database connections
- Thread pools
- Network connections
- Expensive object creation
- Resource-constrained environments

### Best Practices
1. Set appropriate pool size
2. Handle object lifecycle properly
3. Clean objects before reuse
4. Monitor pool usage
5. Handle pool exhaustion gracefully

## Dependency Injection

### Intent
Provide dependencies to objects rather than having them create dependencies themselves.

### Types
- **Constructor Injection**: Dependencies via constructor
- **Setter Injection**: Dependencies via setter methods
- **Interface Injection**: Dependencies via interface
- **Field Injection**: Direct field injection (less preferred)

### Benefits
- Loose coupling
- Testability
- Flexibility
- Single Responsibility Principle
- Dependency Inversion Principle

### Use Cases
- Framework configuration
- Testing (mock injection)
- Service-oriented architectures
- Plugin systems

### Best Practices
1. Prefer constructor injection
2. Use DI containers for complex scenarios
3. Keep injection simple
4. Avoid service locator pattern
5. Document dependencies clearly

## Pattern Selection Guide

### When to Use Singleton
- Exactly one instance needed globally
- Controlled access to shared resource
- Lazy initialization beneficial

### When to Use Factory
- Object creation logic is complex
- Want to decouple creation from usage
- Need to support multiple product types

### When to Use Builder
- Many constructor parameters
- Optional parameters
- Immutable object construction
- Fluent interface desired

### When to Use Prototype
- Object creation is expensive
- Classes vary only in configuration
- Runtime object creation needed

### When to Use Object Pool
- Object creation is expensive
- Objects are frequently created/destroyed
- Resource constraints exist

## Common Mistakes

### Overusing Singleton
- Making everything a singleton
- Creating unnecessary global state
- Making testing difficult

### Factory Complexity
- Over-engineering simple creation
- Too many factory classes
- Not using language features

### Builder Overhead
- Using builder for simple objects
- Unnecessary complexity
- Not validating in build method

### Pattern Misapplication
- Using wrong pattern for problem
- Not understanding trade-offs
- Following patterns blindly


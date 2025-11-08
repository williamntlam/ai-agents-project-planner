# Behavioral Design Patterns

## Overview
Behavioral patterns are concerned with algorithms and the assignment of responsibilities between objects. They describe not just patterns of objects or classes but also the patterns of communication between them.

## Observer Pattern

### Intent
Define a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.

### Structure
- **Subject**: Maintains list of observers, notifies them of changes
- **Observer**: Interface for objects that should be notified
- **Concrete Subject**: Stores state, notifies observers
- **Concrete Observer**: Implements observer interface, maintains reference to subject

### Use Cases
- Event handling systems
- Model-View-Controller (MVC)
- Publish-Subscribe systems
- Real-time data feeds
- UI update mechanisms

### Benefits
- Loose coupling between subject and observers
- Dynamic relationships
- Broadcast communication
- Open/Closed Principle

### Implementation Variants
- **Push Model**: Subject sends detailed data to observers
- **Pull Model**: Observers query subject for data
- **Event Objects**: Encapsulate event information

### Best Practices
1. Use when change to one object requires changing others
2. Avoid tight coupling
3. Consider memory leaks (unsubscribe)
4. Use event objects for complex notifications
5. Consider thread safety

## Strategy Pattern

### Intent
Define a family of algorithms, encapsulate each one, and make them interchangeable. Lets the algorithm vary independently from clients that use it.

### Structure
- **Strategy**: Interface for algorithms
- **Concrete Strategy**: Implements specific algorithm
- **Context**: Uses strategy to execute algorithm

### Use Cases
- Sorting algorithms
- Payment processing methods
- Compression algorithms
- Retry strategies
- Validation rules
- Discount calculation

### Benefits
- Algorithms can be swapped at runtime
- Isolates algorithm implementation
- Eliminates conditional statements
- Open/Closed Principle
- Single Responsibility Principle

### Best Practices
1. Use when you have multiple ways to perform task
2. Isolate algorithm implementation
3. Make strategies interchangeable
4. Consider strategy selection logic
5. Document when to use each strategy

## Command Pattern

### Intent
Encapsulate a request as an object, thereby letting you parameterize clients with different requests, queue requests, and support undoable operations.

### Structure
- **Command**: Interface for commands
- **Concrete Command**: Implements command interface, binds to receiver
- **Receiver**: Knows how to perform operations
- **Invoker**: Asks command to carry out request
- **Client**: Creates command and sets receiver

### Use Cases
- Undo/redo functionality
- Macro recording
- Queuing requests
- Logging requests
- Transaction management
- Remote procedure calls

### Benefits
- Decouples invoker from receiver
- Supports undo/redo
- Can queue and log requests
- Supports composite commands
- Easy to add new commands

### Best Practices
1. Use when you need to parameterize objects
2. Use for undo/redo functionality
3. Keep commands focused and simple
4. Consider command composition
5. Handle command failures gracefully

## Chain of Responsibility Pattern

### Intent
Avoid coupling the sender of a request to its receiver by giving more than one object a chance to handle the request. Chain the receiving objects and pass the request along the chain until an object handles it.

### Structure
- **Handler**: Defines interface for handling requests
- **Concrete Handler**: Handles requests it's responsible for, can access successor
- **Client**: Initiates request to chain

### Use Cases
- Middleware pipelines
- Validation chains
- Error handling
- Event processing
- Request processing
- Logging filters

### Benefits
- Decouples sender and receiver
- Dynamic chain composition
- Can add/remove handlers dynamically
- Single Responsibility Principle

### Best Practices
1. Use when multiple objects can handle request
2. Don't know which handler should process
3. Want to specify handlers dynamically
4. Keep handlers focused
5. Consider chain termination

## State Pattern

### Intent
Allow an object to alter its behavior when its internal state changes. The object will appear to change its class.

### Structure
- **Context**: Maintains reference to current state
- **State**: Interface for state-specific behavior
- **Concrete State**: Implements state-specific behavior

### Use Cases
- State machines
- Workflow systems
- Game state management
- Order processing
- Document approval workflows

### Benefits
- Localizes state-specific behavior
- Makes state transitions explicit
- Eliminates large conditional statements
- Easy to add new states

### Best Practices
1. Use when object behavior depends on state
2. Many conditional statements based on state
3. State transitions are clear
4. Keep states focused
5. Document state transitions

## Template Method Pattern

### Intent
Define the skeleton of an algorithm in an operation, deferring some steps to subclasses. Lets subclasses redefine certain steps without changing algorithm structure.

### Structure
- **Abstract Class**: Defines template method and abstract steps
- **Concrete Class**: Implements abstract steps

### Use Cases
- Framework design
- Algorithm frameworks
- Code generation
- Test frameworks
- Data processing pipelines

### Benefits
- Code reuse
- Controls algorithm structure
- Hooks for customization
- Inversion of Control

### Best Practices
1. Use when algorithm structure is fixed
2. Only some steps vary
3. Want to control algorithm flow
4. Keep template method simple
5. Use hooks for optional steps

## Visitor Pattern

### Intent
Represent an operation to be performed on elements of an object structure. Lets you define new operations without changing classes of elements.

### Structure
- **Visitor**: Interface for visitors
- **Concrete Visitor**: Implements operations
- **Element**: Interface for elements
- **Concrete Element**: Implements element interface, accepts visitors
- **Object Structure**: Collection of elements

### Use Cases
- Compiler design (AST traversal)
- Document processing
- Report generation
- Expression evaluation
- Type checking

### Benefits
- Easy to add new operations
- Groups related operations
- Can accumulate state during traversal
- Separates algorithms from object structure

### Best Practices
1. Use when operations depend on element types
2. Many unrelated operations on object structure
3. Object structure is stable
4. Operations change frequently
5. Consider performance (double dispatch overhead)

## Mediator Pattern

### Intent
Define an object that encapsulates how a set of objects interact. Promotes loose coupling by keeping objects from referring to each other explicitly.

### Structure
- **Mediator**: Defines interface for communication
- **Concrete Mediator**: Implements cooperative behavior
- **Colleague Classes**: Communicate through mediator

### Use Cases
- GUI frameworks (dialog boxes)
- Chat applications
- Air traffic control
- Event coordination
- Workflow management

### Benefits
- Decouples colleagues
- Simplifies object protocols
- Centralizes control
- Easy to add new colleagues

### Best Practices
1. Use when many objects communicate directly
2. Communication is complex
3. Want to reuse objects independently
4. Keep mediator focused
5. Avoid god object mediator

## Memento Pattern

### Intent
Without violating encapsulation, capture and externalize an object's internal state so the object can be restored to this state later.

### Structure
- **Originator**: Creates memento, can restore from memento
- **Memento**: Stores originator's internal state
- **Caretaker**: Safekeeps memento, doesn't operate on it

### Use Cases
- Undo/redo functionality
- Checkpoint systems
- Snapshot functionality
- State restoration
- Transaction rollback

### Benefits
- Preserves encapsulation
- Simplifies originator
- Can store incremental changes
- Supports undo/redo

### Best Practices
1. Use when you need to save/restore state
2. Direct interface would expose implementation
3. Keep mementos immutable
4. Consider memory usage for many mementos
5. Handle memento lifecycle

## Iterator Pattern

### Intent
Provide a way to access elements of an aggregate object sequentially without exposing its underlying representation.

### Structure
- **Iterator**: Interface for accessing elements
- **Concrete Iterator**: Implements iterator interface
- **Aggregate**: Interface for creating iterator
- **Concrete Aggregate**: Implements aggregate interface

### Use Cases
- Collections traversal
- Tree traversal
- Graph traversal
- Database result sets
- Stream processing

### Benefits
- Supports multiple traversals
- Simplifies aggregate interface
- Supports different iteration algorithms
- Single Responsibility Principle

### Best Practices
1. Use when you need to traverse collections
2. Want to hide traversal implementation
3. Support multiple traversal methods
4. Consider thread safety
5. Handle concurrent modifications

## Interpreter Pattern

### Intent
Given a language, define a representation for its grammar along with an interpreter that uses the representation to interpret sentences in the language.

### Structure
- **Abstract Expression**: Declares abstract interpret operation
- **Terminal Expression**: Implements interpret for terminal symbols
- **Nonterminal Expression**: Implements interpret for grammar rules
- **Context**: Contains global information
- **Client**: Builds abstract syntax tree

### Use Cases
- Language interpreters
- Query languages (SQL)
- Regular expressions
- Expression evaluators
- Rule engines

### Benefits
- Easy to implement grammar
- Easy to add new expressions
- Grammar implementation is straightforward

### Best Practices
1. Use for simple languages
2. Grammar is simple
3. Performance is not critical
4. Consider parser generators for complex grammars
5. Keep expressions focused

## Pattern Selection Guide

### When to Use Observer
- Change to one object requires changing others
- Number of dependents is unknown
- Loose coupling desired

### When to Use Strategy
- Multiple algorithms for same task
- Want to switch algorithms at runtime
- Isolate algorithm implementation

### When to Use Command
- Need to parameterize objects
- Need undo/redo
- Need to queue/log requests

### When to Use Chain of Responsibility
- Multiple objects can handle request
- Want to specify handlers dynamically
- Decouple sender and receiver

### When to Use State
- Object behavior depends on state
- Many state-based conditionals
- State transitions are clear

### When to Use Template Method
- Algorithm structure is fixed
- Only some steps vary
- Want code reuse

### When to Use Visitor
- Many operations on object structure
- Operations depend on element types
- Object structure is stable

### When to Use Mediator
- Many objects communicate directly
- Communication is complex
- Want loose coupling

### When to Use Memento
- Need to save/restore state
- Don't want to expose implementation
- Support undo/redo

### When to Use Iterator
- Need to traverse collections
- Hide traversal implementation
- Support multiple traversal methods

## Common Mistakes

### Observer Memory Leaks
- Not unsubscribing observers
- Strong references preventing garbage collection
- Circular references

### Strategy Overuse
- Using strategy for simple conditionals
- Too many strategy classes
- Not documenting strategy selection

### Command Complexity
- Commands doing too much
- Not handling failures
- Complex undo logic

### Chain Termination
- Forgetting to terminate chain
- Infinite loops in chain
- Not handling unhandled requests

### State Explosion
- Too many states
- Complex state transitions
- Not using state machines when appropriate


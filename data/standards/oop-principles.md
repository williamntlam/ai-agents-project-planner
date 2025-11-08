# Object-Oriented Programming Principles

## OOP Fundamentals

### Core Concepts
- **Encapsulation**: Bundling data and methods together
- **Inheritance**: Creating new classes from existing ones
- **Polymorphism**: Same interface, different implementations
- **Abstraction**: Hiding implementation details

### Benefits
- Code reusability
- Modularity
- Maintainability
- Scalability
- Real-world modeling

## Encapsulation

### Definition
Bundling data and methods that operate on that data within a single unit (class), and restricting access to some components.

### Purpose
- Hide implementation details
- Protect data integrity
- Control access
- Reduce coupling

### Implementation
- **Private Members**: Only accessible within class
- **Protected Members**: Accessible in class and subclasses
- **Public Members**: Accessible everywhere
- **Accessors/Mutators**: Controlled access (getters/setters)

### Best Practices
1. Make data private by default
2. Provide controlled access through methods
3. Validate data in setters
4. Don't expose internal implementation
5. Use properties for computed values

### Example
```python
class BankAccount:
    def __init__(self, balance):
        self._balance = balance  # Protected
    
    def get_balance(self):
        return self._balance
    
    def deposit(self, amount):
        if amount > 0:
            self._balance += amount
        else:
            raise ValueError("Amount must be positive")
    
    def withdraw(self, amount):
        if 0 < amount <= self._balance:
            self._balance -= amount
        else:
            raise ValueError("Invalid amount")
```

## Inheritance

### Definition
Mechanism where a new class (derived/child) is created from an existing class (base/parent), inheriting its attributes and methods.

### Types of Inheritance
- **Single Inheritance**: One parent class
- **Multiple Inheritance**: Multiple parent classes
- **Multilevel Inheritance**: Chain of inheritance
- **Hierarchical Inheritance**: Multiple children from one parent
- **Hybrid Inheritance**: Combination of types

### Purpose
- Code reuse
- Extend functionality
- Model "is-a" relationships
- Polymorphism support

### Best Practices
1. Use for "is-a" relationships
2. Don't use for code reuse alone
3. Follow Liskov Substitution Principle
4. Avoid deep inheritance hierarchies
5. Prefer composition when appropriate

### Example
```python
class Animal:
    def __init__(self, name):
        self.name = name
    
    def make_sound(self):
        raise NotImplementedError("Subclass must implement")
    
    def move(self):
        return f"{self.name} is moving"

class Dog(Animal):
    def make_sound(self):
        return f"{self.name} barks"

class Cat(Animal):
    def make_sound(self):
        return f"{self.name} meows"
```

### When to Use Inheritance
- Clear "is-a" relationship
- Need to extend functionality
- Polymorphism required
- Shared behavior and attributes

### When to Avoid Inheritance
- "has-a" relationship (use composition)
- Code reuse only (use composition)
- Deep hierarchies (use composition)
- Tight coupling concerns

## Polymorphism

### Definition
Ability of objects of different types to be accessed through the same interface, with each type providing its own implementation.

### Types

#### Compile-Time Polymorphism (Method Overloading)
- Same method name, different parameters
- Resolved at compile time
- Not directly supported in Python (use default parameters)

#### Runtime Polymorphism (Method Overriding)
- Same method signature in parent and child
- Resolved at runtime
- Based on actual object type

### Purpose
- Flexibility
- Code reuse
- Extensibility
- Interface consistency

### Implementation
- Method overriding
- Abstract methods
- Interfaces
- Duck typing (Python)

### Best Practices
1. Use consistent interfaces
2. Follow Liskov Substitution Principle
3. Document expected behavior
4. Use abstract base classes
5. Test polymorphic behavior

### Example
```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self):
        pass
    
    @abstractmethod
    def perimeter(self):
        pass

class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    def area(self):
        return self.width * self.height
    
    def perimeter(self):
        return 2 * (self.width + self.height)

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius
    
    def area(self):
        return 3.14159 * self.radius ** 2
    
    def perimeter(self):
        return 2 * 3.14159 * self.radius

# Polymorphic usage
def print_area(shape: Shape):
    print(f"Area: {shape.area()}")

rectangle = Rectangle(5, 3)
circle = Circle(4)

print_area(rectangle)  # Works with any Shape
print_area(circle)      # Polymorphism in action
```

## Abstraction

### Definition
Hiding complex implementation details and showing only essential features of an object.

### Purpose
- Simplify complexity
- Focus on what, not how
- Reduce cognitive load
- Enable modularity

### Implementation
- Abstract classes
- Interfaces
- Abstract methods
- Hide implementation details

### Best Practices
1. Expose only necessary interface
2. Hide implementation complexity
3. Use abstract base classes
4. Document abstract interfaces
5. Keep abstractions focused

### Example
```python
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def query(self, sql):
        pass
    
    @abstractmethod
    def close(self):
        pass

class MySQLDatabase(Database):
    def connect(self):
        # Implementation details hidden
        return "Connected to MySQL"
    
    def query(self, sql):
        # Implementation details hidden
        return f"Executed: {sql}"
    
    def close(self):
        # Implementation details hidden
        return "MySQL connection closed"

# Client code uses abstraction
def use_database(db: Database):
    db.connect()
    result = db.query("SELECT * FROM users")
    db.close()
    return result
```

## OOP Design Principles

### Single Responsibility Principle (SRP)
- Class should have one reason to change
- Focused responsibility
- Easier to maintain

### Open/Closed Principle (OCP)
- Open for extension, closed for modification
- Use inheritance and polymorphism
- Enable extension without change

### Liskov Substitution Principle (LSP)
- Subtypes must be substitutable for base types
- Maintain contracts
- Proper inheritance

### Interface Segregation Principle (ISP)
- Clients shouldn't depend on unused interfaces
- Focused interfaces
- Reduce coupling

### Dependency Inversion Principle (DIP)
- Depend on abstractions, not concretions
- Invert dependencies
- Enable flexibility

## Class Design

### Class Responsibilities
- **Single Purpose**: One clear responsibility
- **Cohesion**: Related functionality together
- **Coupling**: Minimize dependencies
- **Naming**: Clear, descriptive names

### Class Relationships

#### Association
- "Uses" relationship
- Objects work together
- Can be bidirectional

#### Aggregation
- "Has-a" relationship
- Part can exist independently
- Weaker relationship

#### Composition
- "Contains" relationship
- Part cannot exist without whole
- Stronger relationship

#### Inheritance
- "Is-a" relationship
- Specialization
- Code reuse

### Best Practices
1. Keep classes focused
2. Minimize dependencies
3. Use composition over inheritance
4. Clear naming
5. Document responsibilities

## Method Design

### Method Responsibilities
- **Single Purpose**: One clear action
- **Clear Naming**: Verb-based names
- **Appropriate Size**: Not too long
- **Parameters**: Minimal, clear

### Method Types
- **Accessors**: Get data (getters)
- **Mutators**: Modify data (setters)
- **Queries**: Return information
- **Commands**: Perform actions
- **Factories**: Create objects

### Best Practices
1. Keep methods small
2. Single responsibility
3. Clear naming
4. Minimal parameters
5. Return appropriate types

## Object Lifecycle

### Creation
- Constructor initialization
- Factory methods
- Builder pattern
- Proper initialization

### Usage
- Encapsulation
- Method calls
- State management
- Error handling

### Destruction
- Cleanup resources
- Finalizers/destructors
- Memory management
- Resource release

## OOP Patterns

### Creational Patterns
- **Factory**: Create objects
- **Builder**: Construct complex objects
- **Singleton**: Single instance
- **Prototype**: Clone objects

### Structural Patterns
- **Adapter**: Interface adaptation
- **Decorator**: Add behavior
- **Facade**: Simplified interface
- **Proxy**: Control access

### Behavioral Patterns
- **Observer**: Notify dependents
- **Strategy**: Interchangeable algorithms
- **Command**: Encapsulate requests
- **Template Method**: Algorithm skeleton

## Common OOP Mistakes

### Overuse of Inheritance
- Using inheritance for code reuse only
- Deep inheritance hierarchies
- Violating LSP
- **Solution**: Prefer composition

### God Classes
- Classes doing too much
- Multiple responsibilities
- Hard to maintain
- **Solution**: Apply SRP, break down

### Tight Coupling
- Too many dependencies
- Hard to test
- Hard to change
- **Solution**: Use interfaces, dependency injection

### Anemic Domain Model
- Data classes without behavior
- Logic in services
- Not true OOP
- **Solution**: Move behavior to domain objects

### Violating Encapsulation
- Exposing internal state
- Public data members
- Breaking encapsulation
- **Solution**: Use accessors, keep data private

## Best Practices Summary

1. **Encapsulate**: Hide implementation, expose interface
2. **Inherit Wisely**: Use for "is-a" relationships
3. **Polymorph**: Use interfaces and abstractions
4. **Abstract**: Hide complexity
5. **Follow SOLID**: Apply OOP principles
6. **Composition**: Prefer over inheritance when appropriate
7. **Small Classes**: Keep classes focused
8. **Clear Naming**: Use descriptive names
9. **Document**: Document class responsibilities
10. **Test**: Design for testability

## Language-Specific Considerations

### Python
- Duck typing
- Multiple inheritance
- Properties
- Magic methods
- Abstract base classes

### Java
- Strong typing
- Single inheritance, multiple interfaces
- Access modifiers
- Abstract classes
- Interfaces

### C#
- Properties
- Events
- LINQ
- Generics
- Extension methods

### JavaScript
- Prototype-based
- Closures
- Functions as first-class
- Dynamic typing
- ES6 classes

## Modern OOP Trends

### Functional Programming Integration
- Immutability
- Pure functions
- Higher-order functions
- Functional composition

### Reactive Programming
- Observable patterns
- Event streams
- Asynchronous processing
- Data flow

### Microservices
- Service-oriented design
- API design
- Distributed systems
- Service boundaries


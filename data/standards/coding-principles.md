# Coding Principles and Best Practices

## Core Programming Principles

### DRY (Don't Repeat Yourself)
**Definition**: Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.

**Purpose**:
- Eliminate code duplication
- Reduce maintenance burden
- Ensure consistency
- Single source of truth

**How to Apply**:
- Extract common code into functions/methods
- Create reusable components
- Use configuration files for constants
- Centralize business logic
- Share code through libraries/modules

**Benefits**:
- Easier maintenance (fix once, applies everywhere)
- Reduced bugs (less code to maintain)
- Consistency across codebase
- Faster development

**When to Violate DRY**:
- Premature abstraction (YAGNI)
- Different contexts requiring different implementations
- Performance-critical code
- When abstraction adds complexity

**Best Practices**:
1. Identify duplication patterns
2. Extract at appropriate level (function, class, module)
3. Don't over-abstract
4. Consider future needs
5. Refactor incrementally

### KISS (Keep It Simple, Stupid)
**Definition**: Most systems work best if they are kept simple rather than made complicated.

**Purpose**:
- Avoid unnecessary complexity
- Improve readability
- Reduce bugs
- Easier maintenance

**How to Apply**:
- Prefer simple solutions over complex ones
- Avoid over-engineering
- Use straightforward algorithms
- Clear, readable code
- Avoid premature optimization

**Benefits**:
- Easier to understand
- Faster to develop
- Fewer bugs
- Easier to maintain
- Better performance (often)

**Best Practices**:
1. Start with simplest solution
2. Add complexity only when needed
3. Question complex solutions
4. Prefer readability over cleverness
5. Regular refactoring to simplify

### YAGNI (You Aren't Gonna Need It)
**Definition**: Don't implement functionality until it is necessary.

**Purpose**:
- Avoid over-engineering
- Focus on current requirements
- Reduce wasted effort
- Faster delivery

**How to Apply**:
- Implement only what's needed now
- Don't add "just in case" features
- Avoid premature abstraction
- Focus on current user stories
- Refactor when needed

**Benefits**:
- Faster development
- Less code to maintain
- Focus on value
- Avoid wasted effort
- Easier to change

**When to Violate YAGNI**:
- Clear future requirements
- Architectural decisions
- Performance requirements
- Security considerations

**Best Practices**:
1. Implement current requirements only
2. Refactor when patterns emerge
3. Don't guess future needs
4. Focus on delivering value
5. Trust refactoring process

### SOLID Principles

#### Single Responsibility Principle (SRP)
**Definition**: A class should have only one reason to change.

**Purpose**:
- Clear responsibilities
- Easier to understand
- Easier to test
- Easier to maintain

**How to Apply**:
- Each class has one job
- Separate concerns
- Extract responsibilities
- Focused classes

**Benefits**:
- Clear code organization
- Easier testing
- Easier maintenance
- Better cohesion

**Example**:
```python
# Bad: Multiple responsibilities
class User:
    def save(self): ...
    def send_email(self): ...
    def validate(self): ...

# Good: Single responsibility
class User:
    def validate(self): ...

class UserRepository:
    def save(self, user): ...

class EmailService:
    def send_email(self, user): ...
```

#### Open/Closed Principle (OCP)
**Definition**: Software entities should be open for extension but closed for modification.

**Purpose**:
- Extend functionality without changing existing code
- Reduce risk of breaking changes
- Support plugin architectures

**How to Apply**:
- Use interfaces/abstract classes
- Strategy pattern
- Dependency injection
- Plugin architectures

**Benefits**:
- Less risk of breaking changes
- Easier to extend
- Better testability
- Flexible design

**Example**:
```python
# Bad: Must modify for new types
class AreaCalculator:
    def calculate(self, shape):
        if isinstance(shape, Rectangle):
            return shape.width * shape.height
        elif isinstance(shape, Circle):
            return 3.14 * shape.radius ** 2

# Good: Open for extension
class Shape:
    def area(self): pass

class Rectangle(Shape):
    def area(self): return self.width * self.height

class Circle(Shape):
    def area(self): return 3.14 * self.radius ** 2
```

#### Liskov Substitution Principle (LSP)
**Definition**: Objects of a superclass should be replaceable with objects of its subclasses without breaking the application.

**Purpose**:
- Ensure proper inheritance
- Maintain contracts
- Enable polymorphism

**How to Apply**:
- Subclasses must honor parent contracts
- Don't weaken preconditions
- Don't strengthen postconditions
- Maintain invariants

**Benefits**:
- Correct inheritance
- Reliable polymorphism
- Easier to reason about code
- Fewer bugs

**Example**:
```python
# Bad: Violates LSP
class Rectangle:
    def set_width(self, w): ...
    def set_height(self, h): ...

class Square(Rectangle):
    def set_width(self, w):
        self.width = w
        self.height = w  # Breaks rectangle contract

# Good: Proper design
class Shape:
    def area(self): pass

class Rectangle(Shape):
    def area(self): return self.width * self.height

class Square(Shape):
    def area(self): return self.side ** 2
```

#### Interface Segregation Principle (ISP)
**Definition**: Clients should not be forced to depend on interfaces they don't use.

**Purpose**:
- Avoid fat interfaces
- Reduce coupling
- Better cohesion

**How to Apply**:
- Create focused interfaces
- Split large interfaces
- Client-specific interfaces
- Avoid "god" interfaces

**Benefits**:
- Less coupling
- Easier to implement
- Clearer contracts
- Better design

**Example**:
```python
# Bad: Fat interface
class Worker:
    def work(self): ...
    def eat(self): ...
    def sleep(self): ...

# Good: Segregated interfaces
class Workable:
    def work(self): ...

class Eatable:
    def eat(self): ...

class Sleepable:
    def sleep(self): ...
```

#### Dependency Inversion Principle (DIP)
**Definition**: Depend on abstractions, not concretions.

**Purpose**:
- Reduce coupling
- Enable flexibility
- Improve testability

**How to Apply**:
- Depend on interfaces/abstract classes
- Use dependency injection
- Invert dependencies
- High-level modules independent of low-level

**Benefits**:
- Loose coupling
- Easy to test
- Flexible design
- Better maintainability

**Example**:
```python
# Bad: Depends on concrete class
class UserService:
    def __init__(self):
        self.repository = MySQLUserRepository()

# Good: Depends on abstraction
class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository
```

## Additional Principles

### Separation of Concerns (SoC)
**Definition**: Separate a computer program into distinct sections, each addressing a separate concern.

**Purpose**:
- Modular design
- Easier maintenance
- Independent development
- Clear boundaries

**How to Apply**:
- Separate by responsibility
- Layer architecture
- Domain boundaries
- Technical vs business logic

**Benefits**:
- Clear organization
- Easier to understand
- Independent changes
- Better testing

### Principle of Least Astonishment
**Definition**: The result of performing some operation should be obvious, consistent, and predictable.

**Purpose**:
- Intuitive APIs
- Predictable behavior
- Better user experience
- Fewer bugs

**How to Apply**:
- Follow conventions
- Consistent naming
- Predictable behavior
- Clear documentation

**Benefits**:
- Easier to use
- Fewer mistakes
- Better developer experience
- Faster development

### Fail Fast
**Definition**: Detect errors as early as possible and fail immediately.

**Purpose**:
- Early error detection
- Easier debugging
- Prevent bad state
- Clear error messages

**How to Apply**:
- Validate inputs early
- Assert invariants
- Type checking
- Clear error messages

**Benefits**:
- Easier debugging
- Prevent cascading failures
- Clear error messages
- Better reliability

### Composition Over Inheritance
**Definition**: Favor object composition over class inheritance.

**Purpose**:
- More flexible
- Avoid inheritance issues
- Better code reuse
- Easier to change

**How to Apply**:
- Use composition
- Prefer interfaces
- Avoid deep hierarchies
- Use delegation

**Benefits**:
- More flexible
- Easier to change
- Avoid inheritance pitfalls
- Better code reuse

## Code Quality Principles

### Readability
**Principles**:
- Code should read like prose
- Clear variable names
- Self-documenting code
- Appropriate comments
- Consistent style

**Best Practices**:
1. Use descriptive names
2. Keep functions small
3. Avoid deep nesting
4. Use whitespace effectively
5. Follow style guides

### Maintainability
**Principles**:
- Easy to understand
- Easy to modify
- Easy to extend
- Well-organized
- Documented

**Best Practices**:
1. Clear structure
2. Modular design
3. Good documentation
4. Version control
5. Regular refactoring

### Testability
**Principles**:
- Easy to test
- Isolated units
- Mockable dependencies
- Fast tests
- Clear test cases

**Best Practices**:
1. Small, focused units
2. Dependency injection
3. Avoid static dependencies
4. Clear interfaces
5. Test-driven development

## Anti-Patterns to Avoid

### God Object
- Object that knows/does too much
- Violates SRP
- Hard to test and maintain
- Solution: Break into smaller objects

### Spaghetti Code
- Unstructured, tangled code
- Hard to follow
- Difficult to maintain
- Solution: Refactor, apply patterns

### Magic Numbers
- Hard-coded numbers without explanation
- Unclear meaning
- Hard to maintain
- Solution: Use named constants

### Copy-Paste Programming
- Duplicating code
- Maintenance nightmare
- Inconsistencies
- Solution: Extract common code

### Premature Optimization
- Optimizing before measuring
- Can add complexity
- May not be needed
- Solution: Profile first, optimize bottlenecks

## Best Practices Summary

1. **Follow DRY**: Eliminate duplication
2. **Keep It Simple**: Avoid unnecessary complexity
3. **YAGNI**: Don't build what you don't need
4. **SOLID Principles**: Apply object-oriented principles
5. **Separate Concerns**: Clear boundaries
6. **Fail Fast**: Detect errors early
7. **Composition**: Prefer composition over inheritance
8. **Readability**: Code should be easy to read
9. **Testability**: Design for testing
10. **Refactor Regularly**: Continuously improve code

## When Principles Conflict

### DRY vs YAGNI
- **DRY**: Eliminate duplication
- **YAGNI**: Don't abstract prematurely
- **Solution**: Extract when pattern is clear, not guessed

### KISS vs DRY
- **KISS**: Keep it simple
- **DRY**: Don't repeat
- **Solution**: Extract when it simplifies, not complicates

### SOLID vs Performance
- **SOLID**: Good design
- **Performance**: Speed requirements
- **Solution**: Measure first, optimize where needed

## Application Guidelines

1. **Start Simple**: Begin with simplest solution
2. **Apply Principles**: Use principles as guidelines
3. **Refactor Incrementally**: Improve code continuously
4. **Measure Impact**: Understand trade-offs
5. **Team Agreement**: Agree on principles to follow
6. **Code Reviews**: Enforce principles in reviews
7. **Documentation**: Document when principles are violated
8. **Continuous Learning**: Keep improving understanding


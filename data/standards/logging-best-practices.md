# Logging Best Practices for Production

## Overview
Effective logging is critical for debugging production issues, monitoring system health, and understanding application behavior. This guide covers comprehensive logging strategies for production environments.

## Logging Fundamentals

### Purpose of Logging
- **Debugging**: Identify and fix bugs
- **Monitoring**: Track system health and performance
- **Auditing**: Record important business events
- **Troubleshooting**: Diagnose production issues
- **Analytics**: Understand user behavior and system usage
- **Compliance**: Meet regulatory requirements

### Logging Principles
1. **Log Everything Important**: But not too much
2. **Structured Logging**: Use structured formats
3. **Appropriate Levels**: Use correct log levels
4. **Context**: Include sufficient context
5. **Performance**: Don't impact application performance
6. **Security**: Don't log sensitive information

## Log Levels

### Standard Log Levels

#### DEBUG
**When to Use**:
- Detailed information for debugging
- Development and troubleshooting
- Verbose diagnostic information
- Step-by-step execution flow

**Characteristics**:
- Most verbose level
- Usually disabled in production
- Useful for development
- Can be expensive

**Example**:
```python
logger.debug("Processing user request", extra={
    "user_id": user_id,
    "request_id": request_id,
    "step": "validation"
})
```

#### INFO
**When to Use**:
- General informational messages
- Application flow milestones
- Important business events
- Confirmation of normal operations

**Characteristics**:
- Normal operational messages
- Useful for understanding flow
- Should be enabled in production
- Moderate volume

**Example**:
```python
logger.info("User logged in successfully", extra={
    "user_id": user_id,
    "ip_address": ip_address,
    "timestamp": datetime.utcnow()
})
```

#### WARNING
**When to Use**:
- Unexpected situations that don't stop execution
- Deprecated feature usage
- Recoverable errors
- Performance concerns

**Characteristics**:
- Indicates potential issues
- Application continues normally
- Should be investigated
- Enabled in production

**Example**:
```python
logger.warning("API rate limit approaching", extra={
    "user_id": user_id,
    "current_rate": current_rate,
    "limit": rate_limit,
    "percentage": (current_rate / rate_limit) * 100
})
```

#### ERROR
**When to Use**:
- Error events that don't stop application
- Failed operations
- Exception handling
- Recoverable failures

**Characteristics**:
- Indicates errors
- Application continues
- Requires attention
- Always enabled

**Example**:
```python
logger.error("Failed to send email", extra={
    "user_id": user_id,
    "email": email,
    "error": str(e),
    "retry_count": retry_count
}, exc_info=True)
```

#### CRITICAL/FATAL
**When to Use**:
- Critical errors that may stop application
- System-level failures
- Data corruption
- Security breaches

**Characteristics**:
- Most severe level
- May stop application
- Immediate attention required
- Always enabled and alerted

**Example**:
```python
logger.critical("Database connection lost", extra={
    "database": db_name,
    "error": str(e),
    "impact": "All database operations failing"
}, exc_info=True)
```

### Log Level Guidelines
- **Development**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Staging**: INFO, WARNING, ERROR, CRITICAL
- **Production**: INFO, WARNING, ERROR, CRITICAL (DEBUG only for specific components)

## Structured Logging

### Why Structured Logging?
- **Searchable**: Easy to query and filter
- **Parseable**: Machine-readable format
- **Consistent**: Standard format across application
- **Analyzable**: Enable log analytics
- **Correlatable**: Easy to correlate related logs

### Formats

#### JSON Format
**Advantages**:
- Machine-readable
- Easy to parse
- Supports nested structures
- Widely supported

**Example**:
```python
import json
import logging

logger.info(json.dumps({
    "level": "INFO",
    "timestamp": "2024-01-15T10:30:00Z",
    "service": "user-service",
    "message": "User created",
    "user_id": "12345",
    "request_id": "abc-123",
    "duration_ms": 45,
    "status": "success"
}))
```

#### Structured Logging Libraries
```python
# Python structlog
import structlog

logger = structlog.get_logger()
logger.info("User created",
    user_id="12345",
    request_id="abc-123",
    duration_ms=45
)

# Output: {"event": "User created", "user_id": "12345", "request_id": "abc-123", "duration_ms": 45}
```

### Key Fields to Include

#### Request Context
- **request_id**: Unique request identifier
- **trace_id**: Distributed tracing ID
- **span_id**: Span identifier
- **user_id**: User identifier
- **session_id**: Session identifier
- **correlation_id**: Correlation identifier

#### Application Context
- **service_name**: Service identifier
- **environment**: Environment (dev, staging, prod)
- **version**: Application version
- **host**: Server hostname
- **instance_id**: Instance identifier

#### Timing Information
- **timestamp**: Event timestamp
- **duration_ms**: Operation duration
- **start_time**: Operation start time
- **end_time**: Operation end time

#### Error Information
- **error_type**: Error class/type
- **error_message**: Error message
- **stack_trace**: Stack trace (for errors)
- **error_code**: Application error code

## Logging Patterns

### Request/Response Logging
**Pattern**: Log incoming requests and outgoing responses

**Implementation**:
```python
import logging
import time

logger = logging.getLogger(__name__)

def log_request(request):
    logger.info("Incoming request", extra={
        "method": request.method,
        "path": request.path,
        "query_params": dict(request.query_params),
        "headers": sanitize_headers(request.headers),
        "request_id": request.headers.get("X-Request-ID"),
        "user_id": get_user_id(request),
        "ip_address": request.client.host
    })

def log_response(request, response, duration_ms):
    logger.info("Outgoing response", extra={
        "method": request.method,
        "path": request.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "request_id": request.headers.get("X-Request-ID"),
        "response_size": len(response.body) if hasattr(response, 'body') else 0
    })
```

### Error Logging
**Pattern**: Comprehensive error logging with context

**Implementation**:
```python
import logging
import traceback

logger = logging.getLogger(__name__)

def log_error(error, context=None):
    logger.error("Error occurred", extra={
        "error_type": type(error).__name__,
        "error_message": str(error),
        "stack_trace": traceback.format_exc(),
        "context": context or {},
        "request_id": get_request_id(),
        "user_id": get_user_id()
    }, exc_info=True)
```

### Performance Logging
**Pattern**: Log slow operations and performance metrics

**Implementation**:
```python
import time
import logging

logger = logging.getLogger(__name__)

def log_performance(operation_name, duration_ms, threshold_ms=1000):
    if duration_ms > threshold_ms:
        logger.warning("Slow operation detected", extra={
            "operation": operation_name,
            "duration_ms": duration_ms,
            "threshold_ms": threshold_ms,
            "request_id": get_request_id()
        })
    else:
        logger.debug("Operation completed", extra={
            "operation": operation_name,
            "duration_ms": duration_ms
        })
```

### Business Event Logging
**Pattern**: Log important business events

**Implementation**:
```python
logger.info("Order placed", extra={
    "event_type": "order.placed",
    "order_id": order_id,
    "user_id": user_id,
    "total_amount": total_amount,
    "currency": "USD",
    "items_count": len(items),
    "payment_method": payment_method,
    "timestamp": datetime.utcnow().isoformat()
})
```

### State Change Logging
**Pattern**: Log important state changes

**Implementation**:
```python
logger.info("User status changed", extra={
    "entity_type": "user",
    "entity_id": user_id,
    "old_status": old_status,
    "new_status": new_status,
    "changed_by": changed_by_user_id,
    "reason": change_reason,
    "timestamp": datetime.utcnow().isoformat()
})
```

## Production Debugging Strategies

### Correlation IDs
**Purpose**: Track requests across services

**Implementation**:
```python
import uuid
import logging

# Generate correlation ID at request start
correlation_id = str(uuid.uuid4())

# Include in all logs
logger = logging.LoggerAdapter(
    logging.getLogger(__name__),
    {"correlation_id": correlation_id}
)

logger.info("Processing request", extra={
    "correlation_id": correlation_id,
    "service": "user-service"
})
```

### Distributed Tracing
**Purpose**: Track requests across distributed systems

**Implementation**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order_id", order_id)
    span.set_attribute("user_id", user_id)
    
    logger.info("Processing order", extra={
        "trace_id": format_trace_id(span.get_span_context().trace_id),
        "span_id": format_span_id(span.get_span_context().span_id),
        "order_id": order_id
    })
```

### Request Tracing
**Pattern**: Include request context in all logs

**Implementation**:
```python
class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        record.ip_address = get_ip_address()
        return True

logger.addFilter(RequestContextFilter())
```

### Log Sampling
**Purpose**: Reduce log volume for high-frequency events

**Implementation**:
```python
import random

def log_with_sampling(message, level="info", sample_rate=0.1):
    if random.random() < sample_rate:
        getattr(logger, level)(message)
    else:
        logger.debug(message)  # Still log at debug level
```

## Security Considerations

### Sensitive Data
**Never Log**:
- Passwords
- Credit card numbers
- Social security numbers
- API keys and tokens
- Personal identification numbers
- Authentication tokens

### Data Masking
**Pattern**: Mask sensitive data in logs

**Implementation**:
```python
def mask_sensitive_data(data, fields_to_mask):
    masked = data.copy()
    for field in fields_to_mask:
        if field in masked:
            masked[field] = "***MASKED***"
    return masked

logger.info("User data", extra=mask_sensitive_data({
    "user_id": user_id,
    "email": email,
    "credit_card": credit_card,
    "ssn": ssn
}, ["credit_card", "ssn"]))
```

### PII (Personally Identifiable Information)
**Guidelines**:
- Minimize PII in logs
- Mask or hash when necessary
- Follow compliance requirements (GDPR, HIPAA)
- Use identifiers instead of names when possible
- Encrypt logs containing PII

## Log Aggregation and Storage

### Centralized Logging
**Benefits**:
- Single source of truth
- Easy searching
- Correlation across services
- Historical analysis
- Alerting

### Log Aggregation Tools

#### ELK Stack (Elasticsearch, Logstash, Kibana)
- **Elasticsearch**: Search and analytics engine
- **Logstash**: Log processing pipeline
- **Kibana**: Visualization and dashboards

#### Splunk
- Enterprise log management
- Powerful search capabilities
- Advanced analytics
- Alerting and monitoring

#### Cloud Services
- **AWS CloudWatch**: AWS-native logging
- **Azure Monitor**: Azure logging solution
- **Google Cloud Logging**: GCP logging service
- **Datadog**: Unified observability platform

### Log Retention
**Guidelines**:
- **Development**: 7-30 days
- **Staging**: 30-90 days
- **Production**: 90 days to 1 year (compliance may require longer)
- **Critical Events**: Permanent retention
- **Compliance**: Follow regulatory requirements

## Logging Best Practices

### Do's
1. **Use Structured Logging**: JSON or structured format
2. **Include Context**: Request IDs, user IDs, correlation IDs
3. **Log at Appropriate Levels**: Use correct log levels
4. **Include Timestamps**: Always include timestamps
5. **Log Errors with Stack Traces**: Include full error context
6. **Log Performance Metrics**: Duration, throughput, latency
7. **Log Business Events**: Important business milestones
8. **Use Correlation IDs**: Track requests across services
9. **Sanitize Sensitive Data**: Never log passwords, tokens
10. **Monitor Log Volume**: Avoid log flooding

### Don'ts
1. **Don't Log Sensitive Information**: Passwords, tokens, PII
2. **Don't Log Too Much**: Avoid excessive logging
3. **Don't Log in Tight Loops**: Performance impact
4. **Don't Use String Concatenation**: Use structured logging
5. **Don't Log Binary Data**: Large or binary data
6. **Don't Ignore Errors**: Always log errors
7. **Don't Use Print Statements**: Use proper logging
8. **Don't Log in Production Debug Mode**: Performance impact
9. **Don't Create Log Files Manually**: Use logging framework
10. **Don't Forget Log Rotation**: Prevent disk space issues

## Debugging Production Issues

### Log Analysis Strategies

#### Search Patterns
```python
# Find all errors for a specific user
"level:ERROR AND user_id:12345"

# Find slow requests
"duration_ms:>1000 AND level:WARNING"

# Find all requests in a time range
"timestamp:[2024-01-15T10:00:00Z TO 2024-01-15T11:00:00Z]"

# Find related logs by correlation ID
"correlation_id:abc-123"
```

#### Common Debugging Queries
- **Error Frequency**: Count errors by type
- **Slow Operations**: Find operations exceeding thresholds
- **User Activity**: Track specific user actions
- **Service Dependencies**: Find service interaction issues
- **Performance Degradation**: Identify performance patterns

### Log Correlation
**Pattern**: Correlate logs across services

**Implementation**:
```python
# Include correlation ID in all services
correlation_id = request.headers.get("X-Correlation-ID")

# All services log with same correlation ID
logger.info("Processing in service A", extra={
    "correlation_id": correlation_id,
    "service": "service-a"
})

logger.info("Processing in service B", extra={
    "correlation_id": correlation_id,
    "service": "service-b"
})
```

### Error Investigation Workflow
1. **Identify Error**: Find error in logs
2. **Get Context**: Retrieve correlation ID, request ID
3. **Trace Request**: Follow request through all services
4. **Check Timing**: Identify when error occurred
5. **Examine Stack Trace**: Understand error cause
6. **Check Related Logs**: Find related events
7. **Identify Pattern**: Look for similar errors
8. **Root Cause**: Determine root cause

## Performance Considerations

### Asynchronous Logging
**Purpose**: Don't block application threads

**Implementation**:
```python
import logging.handlers
import queue

# Use QueueHandler for async logging
log_queue = queue.Queue(-1)
queue_handler = logging.handlers.QueueHandler(log_queue)

# Separate thread processes queue
queue_listener = logging.handlers.QueueListener(
    log_queue,
    file_handler
)
queue_listener.start()
```

### Log Sampling
**Purpose**: Reduce log volume

**Implementation**:
```python
# Sample high-frequency logs
if should_log(operation_name, sample_rate=0.1):
    logger.info("High frequency event", extra={...})
```

### Log Level Configuration
**Purpose**: Control verbosity

**Implementation**:
```python
# Production: INFO and above
# Development: DEBUG and above
logging.basicConfig(level=logging.INFO if is_production else logging.DEBUG)
```

## Monitoring and Alerting

### Key Metrics to Monitor
- **Error Rate**: Percentage of errors
- **Log Volume**: Logs per second
- **Log Latency**: Time to write logs
- **Error Types**: Distribution of error types
- **Slow Operations**: Operations exceeding thresholds

### Alerting Rules
```python
# Alert on high error rate
if error_rate > 0.05:  # 5% error rate
    send_alert("High error rate detected", {
        "error_rate": error_rate,
        "time_window": "last 5 minutes"
    })

# Alert on critical errors
if critical_error_count > 0:
    send_alert("Critical errors detected", {
        "count": critical_error_count,
        "errors": recent_critical_errors
    })
```

## Logging Frameworks

### Python
- **logging**: Standard library
- **structlog**: Structured logging
- **loguru**: Modern logging library

### Java
- **Log4j2**: Apache logging framework
- **Logback**: SLF4J implementation
- **SLF4J**: Logging facade

### JavaScript/Node.js
- **Winston**: Popular logging library
- **Bunyan**: JSON logging
- **Pino**: Fast JSON logger

### Best Practices for Framework Selection
1. **Structured Logging Support**: JSON output
2. **Performance**: Low overhead
3. **Flexibility**: Configurable
4. **Integration**: Works with log aggregation tools
5. **Maintenance**: Actively maintained

## Example: Complete Logging Setup

```python
import logging
import json
import sys
from datetime import datetime
from contextvars import ContextVar

# Context variables for request context
request_id_var = ContextVar('request_id', default=None)
user_id_var = ContextVar('user_id', default=None)

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context
        if request_id_var.get():
            log_data["request_id"] = request_id_var.get()
        if user_id_var.get():
            log_data["user_id"] = user_id_var.get()
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(StructuredFormatter())
logger.addHandler(handler)

# Usage
def process_order(order_id, user_id):
    request_id_var.set(str(uuid.uuid4()))
    user_id_var.set(user_id)
    
    logger.info("Processing order", extra={
        "order_id": order_id,
        "action": "process_order"
    })
    
    try:
        # Process order
        result = process(order_id)
        logger.info("Order processed successfully", extra={
            "order_id": order_id,
            "action": "process_order",
            "status": "success"
        })
        return result
    except Exception as e:
        logger.error("Failed to process order", extra={
            "order_id": order_id,
            "action": "process_order",
            "status": "error",
            "error_type": type(e).__name__
        }, exc_info=True)
        raise
```

## Checklist for Production Logging

- [ ] Structured logging format (JSON)
- [ ] Correlation IDs for request tracking
- [ ] Appropriate log levels configured
- [ ] Sensitive data masked
- [ ] Error logging with stack traces
- [ ] Performance metrics logged
- [ ] Business events logged
- [ ] Centralized log aggregation
- [ ] Log retention policy defined
- [ ] Monitoring and alerting configured
- [ ] Log rotation configured
- [ ] Documentation for log analysis
- [ ] Team trained on log analysis
- [ ] Logging performance tested
- [ ] Compliance requirements met


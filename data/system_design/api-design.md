# API Design Best Practices

## RESTful API Principles

### Resource-Based URLs
- Use nouns, not verbs: `/users` not `/getUsers`
- Use plural nouns: `/users` not `/user`
- Hierarchical structure: `/users/123/posts`
- Avoid deep nesting: limit to 2-3 levels

### HTTP Methods
- **GET**: Retrieve resources (idempotent, safe)
- **POST**: Create resources (not idempotent)
- **PUT**: Update/replace resources (idempotent)
- **PATCH**: Partial updates (idempotent)
- **DELETE**: Remove resources (idempotent)

### HTTP Status Codes
- **2xx Success**: 200 (OK), 201 (Created), 204 (No Content)
- **3xx Redirection**: 301 (Moved), 304 (Not Modified)
- **4xx Client Error**: 400 (Bad Request), 401 (Unauthorized), 404 (Not Found), 409 (Conflict)
- **5xx Server Error**: 500 (Internal Error), 503 (Service Unavailable)

## API Versioning

### Versioning Strategies
1. **URL Versioning**: `/v1/users`, `/v2/users`
2. **Header Versioning**: `Accept: application/vnd.api+json;version=1`
3. **Query Parameter**: `/users?version=1`

### Best Practices
1. **Version Early**: Start with versioning from the beginning
2. **Backward Compatibility**: Maintain backward compatibility when possible
3. **Deprecation Policy**: Clearly communicate deprecation timelines
4. **Documentation**: Document all versions and changes

## Request and Response Design

### Request Best Practices
1. **Query Parameters**: Use for filtering, sorting, pagination
2. **Request Body**: Use for complex data in POST/PUT/PATCH
3. **Validation**: Validate all input data
4. **Content-Type**: Specify appropriate content types

### Response Best Practices
1. **Consistent Structure**: Use consistent response format
2. **Error Format**: Standardize error response format
3. **Pagination**: Implement pagination for list endpoints
4. **Metadata**: Include useful metadata (timestamps, version, etc.)

### Example Response Structure
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0"
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100
  }
}
```

## Authentication and Authorization

### Authentication Methods
1. **API Keys**: Simple but less secure
2. **OAuth 2.0**: Industry standard for authorization
3. **JWT (JSON Web Tokens)**: Stateless authentication
4. **Basic Auth**: Simple but requires HTTPS

### Best Practices
1. **HTTPS Only**: Always use HTTPS in production
2. **Token Expiration**: Set appropriate token expiration times
3. **Refresh Tokens**: Implement refresh token mechanism
4. **Rate Limiting**: Implement rate limiting per API key/user
5. **Scope-Based Authorization**: Use scopes for fine-grained access control

## Rate Limiting

### Strategies
1. **Fixed Window**: Limit requests per fixed time window
2. **Sliding Window**: More accurate, tracks requests in sliding window
3. **Token Bucket**: Allows bursts up to bucket capacity
4. **Leaky Bucket**: Smooths out request rate

### Best Practices
1. **Clear Limits**: Communicate rate limits clearly
2. **Rate Limit Headers**: Include rate limit info in response headers
3. **Graceful Degradation**: Return 429 (Too Many Requests) with retry-after
4. **Different Limits**: Different limits for different endpoints/users

## API Documentation

### Best Practices
1. **OpenAPI/Swagger**: Use standard documentation formats
2. **Examples**: Include request/response examples
3. **Error Scenarios**: Document all possible error responses
4. **Interactive**: Provide interactive API explorer
5. **Keep Updated**: Maintain documentation as API evolves

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "abc123"
  }
}
```

### Best Practices
1. **Consistent Format**: Use consistent error response structure
2. **Error Codes**: Use machine-readable error codes
3. **Human-Readable Messages**: Include user-friendly messages
4. **Request IDs**: Include request IDs for debugging
5. **Logging**: Log errors with sufficient context

## Pagination

### Pagination Strategies
1. **Offset-Based**: `?page=1&limit=20`
2. **Cursor-Based**: `?cursor=abc123&limit=20`
3. **Keyset Pagination**: More efficient for large datasets

### Best Practices
1. **Default Limits**: Set reasonable default page sizes
2. **Maximum Limits**: Enforce maximum page size
3. **Metadata**: Include pagination metadata in response
4. **Links**: Provide next/previous page links

## API Testing

### Best Practices
1. **Unit Tests**: Test individual endpoints
2. **Integration Tests**: Test complete workflows
3. **Contract Testing**: Test API contracts
4. **Load Testing**: Test under expected load
5. **Security Testing**: Test for vulnerabilities

## GraphQL Considerations

### When to Use GraphQL
- Complex data requirements
- Mobile applications with limited bandwidth
- Need for flexible queries
- Multiple client types

### Best Practices
1. **Schema Design**: Design clear, intuitive schemas
2. **Query Complexity**: Limit query complexity
3. **Caching**: Implement appropriate caching strategies
4. **Rate Limiting**: Apply rate limiting at resolver level
5. **Error Handling**: Use GraphQL error format


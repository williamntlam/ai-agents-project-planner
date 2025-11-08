# Security Best Practices

## Overview
Security is a critical aspect of software development. This guide covers comprehensive security best practices for application development, covering authentication, authorization, data protection, input validation, and more.

## Authentication and Authorization

### Authentication Best Practices

#### Password Security
**Guidelines**:
- **Never Store Plain Text**: Always hash passwords
- **Use Strong Hashing**: Use bcrypt, Argon2, or scrypt
- **Salt Passwords**: Use unique salt per password
- **Enforce Complexity**: Require strong passwords
- **Password History**: Prevent password reuse
- **Account Lockout**: Lock after failed attempts

**Implementation**:
```python
import bcrypt

# Hashing password
def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Verifying password
def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

**Password Policy**:
- Minimum 12 characters (8 minimum, 12 recommended)
- Mix of uppercase, lowercase, numbers, special characters
- No common passwords
- No personal information
- Regular password expiration (optional, controversial)

#### Multi-Factor Authentication (MFA)
**Benefits**:
- Additional security layer
- Protection against password theft
- Compliance requirements
- Reduced account compromise risk

**Implementation**:
- **TOTP**: Time-based one-time passwords
- **SMS**: SMS-based codes (less secure)
- **Email**: Email-based codes
- **Hardware Tokens**: Physical security keys
- **Biometric**: Fingerprint, face recognition

**Best Practices**:
1. Require MFA for sensitive operations
2. Support backup codes
3. Allow MFA device management
4. Notify on MFA changes
5. Support multiple MFA methods

#### Session Management
**Guidelines**:
- **Secure Cookies**: Use HttpOnly, Secure, SameSite flags
- **Session Timeout**: Implement appropriate timeouts
- **Session Rotation**: Rotate on privilege changes
- **Concurrent Sessions**: Limit if needed
- **Session Storage**: Secure server-side storage

**Implementation**:
```python
# Secure session configuration
session_config = {
    'httponly': True,      # Prevent XSS
    'secure': True,         # HTTPS only
    'samesite': 'Strict',   # CSRF protection
    'max_age': 3600,        # 1 hour timeout
    'session_cookie_name': 'session_id'
}
```

**Session Security**:
- Use cryptographically secure session IDs
- Regenerate session ID on login
- Invalidate on logout
- Clear session on timeout
- Monitor for session hijacking

#### Token-Based Authentication
**JWT (JSON Web Tokens)**:
- **Secure Storage**: Never store in localStorage (XSS risk)
- **Short Expiration**: Use short-lived tokens
- **Refresh Tokens**: Implement refresh mechanism
- **Token Rotation**: Rotate refresh tokens
- **Revocation**: Support token revocation

**Implementation**:
```python
import jwt
from datetime import datetime, timedelta

def create_access_token(user_id, secret_key):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(minutes=15),  # Short-lived
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')

def create_refresh_token(user_id, secret_key):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7),  # Longer-lived
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')
```

**OAuth 2.0**:
- Use authorization code flow (not implicit)
- Implement PKCE for public clients
- Validate state parameter (CSRF protection)
- Verify token signatures
- Check token expiration

### Authorization Best Practices

#### Principle of Least Privilege
**Definition**: Grant minimum necessary permissions

**Implementation**:
- Role-based access control (RBAC)
- Attribute-based access control (ABAC)
- Permission-based access control
- Regular access reviews
- Automatic permission revocation

#### Role-Based Access Control (RBAC)
**Structure**:
- **Roles**: Collections of permissions
- **Permissions**: Specific actions
- **Users**: Assigned roles
- **Hierarchy**: Role inheritance

**Best Practices**:
1. Define clear roles
2. Assign minimal permissions
3. Regular access reviews
4. Document role purposes
5. Audit role assignments

#### Access Control Lists (ACL)
**Use Cases**:
- Fine-grained permissions
- Resource-level access
- Dynamic permissions
- Complex authorization rules

**Implementation**:
```python
def check_permission(user, resource, action):
    # Check user permissions
    if user.has_permission(resource, action):
        return True
    
    # Check role permissions
    for role in user.roles:
        if role.has_permission(resource, action):
            return True
    
    return False
```

## Input Validation and Sanitization

### Validation Principles
**Guidelines**:
- **Validate All Input**: Never trust user input
- **Whitelist Approach**: Allow only known good values
- **Validate on Server**: Client-side validation is not enough
- **Type Checking**: Validate data types
- **Length Limits**: Enforce maximum lengths
- **Format Validation**: Validate formats (email, phone, etc.)

### Common Vulnerabilities

#### SQL Injection
**Prevention**:
- Use parameterized queries
- Use ORM with parameterization
- Input validation
- Least privilege database users
- Stored procedures (with caution)

**Example**:
```python
# BAD: SQL Injection vulnerable
query = f"SELECT * FROM users WHERE username = '{username}'"

# GOOD: Parameterized query
query = "SELECT * FROM users WHERE username = %s"
cursor.execute(query, (username,))
```

#### Cross-Site Scripting (XSS)
**Types**:
- **Stored XSS**: Malicious script stored in database
- **Reflected XSS**: Script reflected in response
- **DOM XSS**: Client-side script injection

**Prevention**:
- Output encoding/escaping
- Content Security Policy (CSP)
- Input validation
- HttpOnly cookies
- Sanitize user input

**Implementation**:
```python
import html

# Escape HTML output
def render_user_content(content):
    return html.escape(content)

# Use template engines with auto-escaping
# Django, Jinja2, etc. escape by default
```

#### Cross-Site Request Forgery (CSRF)
**Prevention**:
- CSRF tokens
- SameSite cookie attribute
- Double-submit cookies
- Origin/Referer checking
- Custom headers

**Implementation**:
```python
# Generate CSRF token
csrf_token = generate_csrf_token()

# Include in forms
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    ...
</form>

# Validate on server
def validate_csrf_token(request_token, session_token):
    return request_token == session_token and request_token is not None
```

#### Command Injection
**Prevention**:
- Avoid executing user input as commands
- Use parameterized APIs
- Validate and sanitize input
- Use safe alternatives
- Least privilege execution

**Example**:
```python
# BAD: Command injection vulnerable
import os
os.system(f"rm {user_input}")  # Dangerous!

# GOOD: Use safe APIs
import shutil
if os.path.exists(user_input) and is_safe_path(user_input):
    os.remove(user_input)
```

#### Path Traversal
**Prevention**:
- Validate file paths
- Use absolute paths
- Restrict to allowed directories
- Sanitize file names
- Use path normalization

**Implementation**:
```python
import os

def safe_file_access(user_path, base_directory):
    # Normalize path
    normalized = os.path.normpath(user_path)
    
    # Ensure it's within base directory
    full_path = os.path.join(base_directory, normalized)
    
    # Verify it's still within base
    if not full_path.startswith(os.path.abspath(base_directory)):
        raise ValueError("Invalid path")
    
    return full_path
```

### Input Validation Patterns

#### Email Validation
```python
import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    
    # Additional checks
    if len(email) > 254:  # RFC 5321 limit
        raise ValueError("Email too long")
    
    return email.lower().strip()
```

#### URL Validation
```python
from urllib.parse import urlparse

def validate_url(url):
    parsed = urlparse(url)
    
    # Only allow http and https
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("Invalid URL scheme")
    
    # Check for valid domain
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    
    return url
```

#### Numeric Validation
```python
def validate_positive_integer(value, max_value=None):
    try:
        num = int(value)
        if num < 0:
            raise ValueError("Must be positive")
        if max_value and num > max_value:
            raise ValueError(f"Must be <= {max_value}")
        return num
    except ValueError:
        raise ValueError("Invalid integer")
```

## Data Protection

### Encryption

#### Encryption at Rest
**Purpose**: Protect stored data

**Implementation**:
- Database encryption
- File system encryption
- Application-level encryption
- Key management
- Encryption key rotation

**Best Practices**:
1. Encrypt sensitive data
2. Use strong encryption algorithms (AES-256)
3. Secure key management
4. Regular key rotation
5. Encrypt backups

#### Encryption in Transit
**Purpose**: Protect data during transmission

**Implementation**:
- TLS/SSL for all connections
- HTTPS for web traffic
- Encrypted database connections
- API encryption
- Certificate validation

**Best Practices**:
1. Always use HTTPS
2. Enforce TLS 1.2 or higher
3. Validate certificates
4. Use strong cipher suites
5. Disable weak protocols

#### Key Management
**Principles**:
- Never hardcode keys
- Use key management services
- Rotate keys regularly
- Separate keys per environment
- Secure key storage

**Tools**:
- AWS KMS
- HashiCorp Vault
- Azure Key Vault
- Google Cloud KMS

### Data Masking
**Purpose**: Hide sensitive data in non-production environments

**Implementation**:
```python
def mask_email(email):
    if '@' in email:
        local, domain = email.split('@', 1)
        masked_local = local[0] + '*' * (len(local) - 1)
        return f"{masked_local}@{domain}"
    return email

def mask_credit_card(card_number):
    if len(card_number) >= 4:
        return '*' * (len(card_number) - 4) + card_number[-4:]
    return '*' * len(card_number)
```

### Data Anonymization
**Purpose**: Remove PII while maintaining data utility

**Techniques**:
- Generalization
- Suppression
- Perturbation
- Pseudonymization
- K-anonymity

## API Security

### API Authentication
**Methods**:
- API keys
- OAuth 2.0
- JWT tokens
- Basic authentication (with HTTPS)

**Best Practices**:
1. Require authentication for all endpoints
2. Use HTTPS only
3. Implement rate limiting
4. Validate all inputs
5. Use appropriate authentication method

### API Authorization
**Implementation**:
- Scope-based authorization
- Resource-level permissions
- Role-based access
- Attribute-based access

### Rate Limiting
**Purpose**: Prevent abuse and DoS attacks

**Implementation**:
```python
from functools import wraps
from time import time

rate_limits = {}

def rate_limit(max_requests=100, window_seconds=60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = get_client_id()
            now = time()
            key = f"{client_id}:{func.__name__}"
            
            if key not in rate_limits:
                rate_limits[key] = []
            
            # Remove old requests
            rate_limits[key] = [
                req_time for req_time in rate_limits[key]
                if now - req_time < window_seconds
            ]
            
            if len(rate_limits[key]) >= max_requests:
                raise RateLimitExceeded("Too many requests")
            
            rate_limits[key].append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### API Security Headers
**Important Headers**:
- **Content-Security-Policy**: XSS protection
- **X-Frame-Options**: Clickjacking protection
- **X-Content-Type-Options**: MIME sniffing protection
- **Strict-Transport-Security**: HTTPS enforcement
- **X-XSS-Protection**: XSS filter

## Secrets Management

### Best Practices
1. **Never Commit Secrets**: Use .gitignore
2. **Environment Variables**: Store in environment
3. **Secret Management Tools**: Use dedicated tools
4. **Rotation**: Rotate secrets regularly
5. **Access Control**: Limit access to secrets
6. **Audit Logging**: Log secret access

### Secret Storage
**Options**:
- Environment variables
- Secret management services
- Encrypted configuration files
- Hardware security modules (HSM)

**Example**:
```python
import os
from cryptography.fernet import Fernet

# Load from environment
api_key = os.getenv('API_KEY')
if not api_key:
    raise ValueError("API_KEY not set")

# Use secret management service
# AWS Secrets Manager, HashiCorp Vault, etc.
```

## Dependency Security

### Dependency Management
**Best Practices**:
1. **Keep Updated**: Regularly update dependencies
2. **Vulnerability Scanning**: Scan for known vulnerabilities
3. **Minimal Dependencies**: Use only necessary dependencies
4. **Trusted Sources**: Use trusted package repositories
5. **Version Pinning**: Pin versions for reproducibility
6. **Security Advisories**: Monitor security advisories

### Vulnerability Scanning
**Tools**:
- **OWASP Dependency-Check**: Dependency vulnerability scanner
- **Snyk**: Security scanning for dependencies
- **WhiteSource**: Open source security management
- **GitHub Dependabot**: Automated dependency updates

**Process**:
1. Regular scanning
2. Review vulnerabilities
3. Update or replace vulnerable dependencies
4. Test after updates
5. Monitor for new vulnerabilities

## Error Handling and Information Disclosure

### Secure Error Messages
**Guidelines**:
- Don't expose sensitive information
- Don't reveal system internals
- Use generic error messages for users
- Log detailed errors server-side
- Different messages for users vs. logs

**Example**:
```python
# BAD: Exposes sensitive information
try:
    db.execute(query)
except Exception as e:
    return f"Database error: {e}"  # May expose DB structure

# GOOD: Generic user message, detailed logging
try:
    db.execute(query)
except Exception as e:
    logger.error("Database error", exc_info=True, extra={
        "query": query,
        "error": str(e)
    })
    return "An error occurred. Please try again later."
```

### Error Logging
**Best Practices**:
1. Log detailed errors server-side
2. Include context (user, request, timestamp)
3. Don't log sensitive data
4. Use appropriate log levels
5. Monitor error rates

## Security Headers

### HTTP Security Headers
**Essential Headers**:
```python
security_headers = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Content-Security-Policy': "default-src 'self'",
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=()'
}
```

## Secure Development Practices

### Secure Coding Guidelines
1. **Input Validation**: Validate all inputs
2. **Output Encoding**: Encode all outputs
3. **Error Handling**: Secure error handling
4. **Authentication**: Strong authentication
5. **Authorization**: Proper authorization
6. **Cryptography**: Use proven libraries
7. **Session Management**: Secure sessions
8. **Logging**: Secure logging practices

### Code Review Security Checklist
- [ ] Input validation implemented
- [ ] Output encoding used
- [ ] Authentication required
- [ ] Authorization checked
- [ ] Sensitive data protected
- [ ] Error handling secure
- [ ] Dependencies secure
- [ ] Secrets not hardcoded
- [ ] SQL injection prevented
- [ ] XSS prevented
- [ ] CSRF protection implemented

### Security Testing
**Types**:
- **Static Analysis**: Code analysis tools
- **Dynamic Analysis**: Runtime testing
- **Penetration Testing**: Manual security testing
- **Vulnerability Scanning**: Automated scanning
- **Dependency Scanning**: Dependency vulnerabilities

**Tools**:
- **OWASP ZAP**: Web application security scanner
- **Burp Suite**: Web vulnerability scanner
- **SonarQube**: Code quality and security
- **Bandit**: Python security linter

## Compliance and Regulations

### Common Regulations
- **GDPR**: General Data Protection Regulation (EU)
- **HIPAA**: Health Insurance Portability and Accountability Act (US)
- **PCI DSS**: Payment Card Industry Data Security Standard
- **SOC 2**: Service Organization Control 2
- **ISO 27001**: Information security management

### Compliance Best Practices
1. **Understand Requirements**: Know applicable regulations
2. **Data Mapping**: Map data flows
3. **Privacy by Design**: Build privacy in
4. **Documentation**: Maintain compliance docs
5. **Regular Audits**: Conduct compliance audits
6. **Incident Response**: Have response procedures

## Security Monitoring

### Security Monitoring Practices
1. **Log Analysis**: Monitor security logs
2. **Anomaly Detection**: Detect unusual patterns
3. **Intrusion Detection**: Detect intrusions
4. **Alerting**: Alert on security events
5. **Incident Response**: Respond to incidents

### Key Security Metrics
- Failed login attempts
- Unauthorized access attempts
- Suspicious API usage
- Data access patterns
- Error rates
- Performance anomalies

## Incident Response

### Incident Response Plan
1. **Detection**: Identify security incidents
2. **Containment**: Contain the incident
3. **Eradication**: Remove threat
4. **Recovery**: Restore systems
5. **Lessons Learned**: Post-incident review

### Incident Response Checklist
- [ ] Incident detected and confirmed
- [ ] Incident response team notified
- [ ] Containment measures implemented
- [ ] Evidence preserved
- [ ] Impact assessed
- [ ] Remediation performed
- [ ] Systems restored
- [ ] Post-incident review conducted
- [ ] Documentation updated

## Security Best Practices Summary

### Authentication & Authorization
- Strong password policies
- Multi-factor authentication
- Secure session management
- Principle of least privilege
- Regular access reviews

### Input Validation
- Validate all inputs
- Use whitelist approach
- Prevent injection attacks
- Sanitize outputs
- Validate on server

### Data Protection
- Encrypt sensitive data
- Use HTTPS/TLS
- Secure key management
- Mask/anonymize PII
- Secure backups

### API Security
- Require authentication
- Implement authorization
- Rate limiting
- Input validation
- Security headers

### Secrets Management
- Never commit secrets
- Use secret management tools
- Rotate regularly
- Limit access
- Audit access

### Secure Development
- Security code reviews
- Vulnerability scanning
- Security testing
- Dependency management
- Security training

### Monitoring & Response
- Security monitoring
- Log analysis
- Incident response plan
- Regular audits
- Continuous improvement

## Security Checklist

### Development
- [ ] Input validation implemented
- [ ] Output encoding used
- [ ] Authentication implemented
- [ ] Authorization checked
- [ ] Sensitive data encrypted
- [ ] Secrets not hardcoded
- [ ] Dependencies secure
- [ ] Error handling secure
- [ ] Security headers configured
- [ ] HTTPS enforced

### Deployment
- [ ] Security testing completed
- [ ] Vulnerabilities addressed
- [ ] Secrets properly configured
- [ ] Security monitoring enabled
- [ ] Incident response plan ready
- [ ] Access controls configured
- [ ] Logging configured
- [ ] Backups encrypted
- [ ] Compliance requirements met

### Operations
- [ ] Security monitoring active
- [ ] Regular security audits
- [ ] Incident response procedures
- [ ] Access reviews scheduled
- [ ] Security updates applied
- [ ] Logs reviewed regularly
- [ ] Vulnerability scanning active
- [ ] Security training current


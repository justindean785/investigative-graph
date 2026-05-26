# Security Policy

## Security Status

This application has undergone a comprehensive security audit and all critical vulnerabilities have been addressed.

### Latest Security Improvements (2026-05-26)

✅ **Critical Security Fixes Implemented:**
- **SSRF Protection**: URL ingestion endpoint now blocks requests to internal/private networks (loopback, RFC 1918, link-local, cloud metadata)
- **CORS Restrictions**: Changed from wildcard (`*`) to explicit origin whitelist (defaults to `http://localhost:3000`)
- **API Key Security**: Removed hardcoded fallback API key from frontend bundle
- **Input Validation**: Status fields now properly validated against allowed values
- **Prompt Injection Protection**: AI chat context sanitizes user-supplied data to prevent prompt injection attacks

### Security Features

- 🔒 SSRF protection with IP address validation
- 🔒 Restricted CORS policy (configurable via `CORS_ORIGINS` env var)
- 🔒 API key authentication on all endpoints
- 🔒 Input validation using Pydantic models with Literal types
- 🔒 Sanitized AI prompts with truncation and delimiter wrapping
- 🔒 Parent resource validation to prevent orphaned data
- 🔒 Thread-safe operations in concurrent environments

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by:

1. **DO NOT** open a public GitHub issue
2. Email the maintainers with details about the vulnerability
3. Include steps to reproduce, potential impact, and suggested fixes if available

You can expect:
- An initial response within 48 hours
- Regular updates on the investigation and remediation
- Credit in the security advisory if you wish (or remain anonymous)

## Deployment Security Recommendations

When deploying to production:

1. **Set a strong API key**: Change `API_KEY` environment variable from the default
2. **Configure CORS**: Set `CORS_ORIGINS` to your actual frontend URL(s)
3. **Use HTTPS**: Always serve the application over HTTPS in production
4. **Secure MongoDB**: Use authentication and restrict network access
5. **Rotate API keys**: Regularly update API keys and credentials
6. **Monitor logs**: Review server logs for suspicious activity
7. **Keep dependencies updated**: Regularly update Python and npm packages

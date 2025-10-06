# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

The BabyShield team takes security vulnerabilities seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **GitHub Security Advisories**: Use our [private vulnerability reporting](https://github.com/BabyShield/babyshield-backend/security/advisories/new)

### What to Include

Please include as much of the following information as possible:

- Type of vulnerability (e.g., SQL injection, XSS, authentication bypass)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours of submission
- **Status Update**: Within 7 days with detailed plan
- **Resolution**: We aim to patch critical vulnerabilities within 30 days

### Disclosure Policy

- Report vulnerabilities privately first
- Allow us reasonable time to fix the issue before public disclosure
- We will credit you in our security advisories (unless you prefer anonymity)

### Security Best Practices

For users of this API:

- Always use HTTPS in production
- Keep dependencies up to date
- Use environment variables for sensitive configuration
- Enable rate limiting and request validation
- Review our security documentation for deployment guidelines

## Security Updates

Subscribe to security advisories:
- Watch this repository for security alerts
- Enable Dependabot alerts in your fork

Thank you for helping keep BabyShield and our community safe! 🔒

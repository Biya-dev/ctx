# Security Policy

## Supported Versions

Currently, only the latest release of `ctx` receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Security is a high priority for `ctx`, especially because it scans local filesystems and environment variables.

If you discover a vulnerability, **do not open a public GitHub issue**.

Instead, please email the maintainer directly or use the GitHub Security Advisory feature to report it privately.

We will acknowledge receipt of your vulnerability report within 48 hours and strive to send you regular updates about our progress. If you report a vulnerability, we will work with you to assess the issue, develop a fix, and coordinate the disclosure.

### What is considered a vulnerability?
- Path traversal exploits during file scanning.
- Leaking environment variables or secrets into exported context files without explicit user intent.
- Malicious code execution triggered by parsing compromised repository files (e.g., malformed `package.json` or `.git` objects).

Thank you for helping keep `ctx` secure!

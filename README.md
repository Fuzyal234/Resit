# OTP Messenger — Secure One Time Pad Application

**Classification:** OFFICIAL USE ONLY  
**Compliance:** ASD STIG V5R3 | NIST SP 800-52 Rev 2 | Container Platform SRG V2R1  

---

## Overview

Browser-based One Time Pad (OTP) encryption tool. Provides information-theoretically secure message encryption when:
- The key is kept secret
- The key is never reused
- Key material is distributed via a separate, approved secure channel

## Architecture

```
[Client Browser]
      │ HTTPS (TLS 1.2/1.3 — NIST 800-52 cipher suites)
      ▼
[Nginx — Port 443]          ← ingress controller, TLS termination,
      │ HTTP (internal)        rate limiting, security headers
      ▼
[Flask / Gunicorn — Port 5000 (internal only)]
      │                     ← OTP logic, CSRF, session management,
      ▼                        structured STIG-compliant logging
[Logs Volume]
```

## Quick Start

### 1. Generate TLS certificates
```bash
make certs
```
> This generates a 4096-bit RSA key, SHA-256 self-signed cert, and 4096-bit DH parameters.
> The DH parameter generation may take 5–15 minutes.

### 2. Build and start
```bash
make build
make up
```

### 3. Access the application
```
https://localhost
```
> Accept the self-signed certificate warning in your browser.
> In production, replace with a CA-issued certificate.

### 4. View logs
```bash
make logs
```

### 5. TLS compliance verification
```bash
make test-tls
```

---

## Security Assessment

| Implementation | CAT I | CAT II | CAT III | Authorised |
|---|---|---|---|---|
| Original (baseline) | 5 | 9 | 3 | NO |
| Final (hardened) | 0 | 0 | 3* | CONDITIONAL |

*Accepted risks — see `security_assessment/final_assessment.md`

Full reports:
- [`security_assessment/original_assessment.md`](security_assessment/original_assessment.md)
- [`security_assessment/final_assessment.md`](security_assessment/final_assessment.md)
- [`security_assessment/comparison.md`](security_assessment/comparison.md)

---

## Production Deployment Checklist

- [ ] Replace `certs/server.crt` and `certs/server.key` with CA-issued certificate
- [ ] Deploy on FIPS 140-2 enabled host OS (e.g. RHEL 8/9 with `fips=1`)
- [ ] Inject `SECRET_KEY` from a secrets manager (Vault, AWS Secrets Manager)
- [ ] Configure centralised log aggregation (SIEM) for audit log retention
- [ ] Document OTP key distribution procedure in Key Management Policy
- [ ] Run `make scan-final` and review Trivy output before deployment
- [ ] Set up log rotation and archival policy per STIG retention requirements

---

## Project Structure

```
.
├── docker-compose.yml              # Final production compose
├── Makefile                        # Build, run, scan commands
├── certs/
│   ├── generate_certs.sh           # TLS cert + DH param generation
│   └── openssl.cnf                 # OpenSSL config (RSA-4096, SHA-256)
├── flask_app/                      # Hardened Flask application
│   ├── app.py                      # Application + OTP logic
│   ├── config.py                   # Security configuration
│   ├── Dockerfile                  # Multi-stage, non-root
│   ├── requirements.txt
│   ├── templates/                  # Jinja2 templates
│   └── static/                     # CSS, JS
├── nginx/                          # NIST 800-52 nginx
│   ├── nginx.conf                  # TLS 1.2/1.3, security headers
│   └── Dockerfile
├── original/                       # Baseline (insecure) implementation
│   ├── docker-compose.yml
│   ├── flask_app/
│   └── nginx/
└── security_assessment/
    ├── original_assessment.md
    ├── final_assessment.md
    └── comparison.md
```

---

## NIST SP 800-52 Rev 2 — TLS Cipher Suites Implemented

**TLS 1.3 (automatic):**
- TLS_AES_256_GCM_SHA384
- TLS_AES_128_GCM_SHA256
- TLS_CHACHA20_POLY1305_SHA256

**TLS 1.2 (configured):**
- ECDHE-ECDSA-AES256-GCM-SHA384
- ECDHE-RSA-AES256-GCM-SHA384
- ECDHE-ECDSA-AES128-GCM-SHA256
- ECDHE-RSA-AES128-GCM-SHA256
- ECDHE-ECDSA-CHACHA20-POLY1305
- ECDHE-RSA-CHACHA20-POLY1305
- DHE-RSA-AES256-GCM-SHA384
- DHE-RSA-AES128-GCM-SHA256

Disabled: SSLv2, SSLv3, TLS 1.0, TLS 1.1, all non-AEAD suites, all NULL/EXPORT/RC4/DES/3DES suites.

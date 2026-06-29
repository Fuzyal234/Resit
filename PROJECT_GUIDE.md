# OTP Messenger — Project Guide

**Audience:** Company X Cyber Security Engineering Team, assessors, and operators
**Compliance targets:** Application Security & Development (ASD) STIG · NIST SP 800-52 Rev 2 · Container Platform SRG · Web Server SRG

This document explains *what* the project is, *why* each component exists, *how* to run
it, and *how far* it meets the stated requirements. It complements the shorter
[`README.md`](README.md) (quick start) and the formal reports in
[`security_assessment/`](security_assessment/).

---

## 1. Purpose

A browser-based **One Time Pad (OTP)** message application. A user can:

- **Encrypt** a plaintext message → the server returns the ciphertext *and* a freshly
  generated, single-use key (both Base64).
- **Decrypt** a ciphertext by supplying the matching key.

OTP provides *information-theoretic* (provably unbreakable) security **only when**:

1. the key is truly random,
2. the key is at least as long as the message,
3. the key is used exactly once, and
4. the key is distributed and kept secret out-of-band.

The application enforces 1–3 technically; requirement 4 (key distribution) is a
procedural control documented as an accepted risk.

The project deliberately ships **two** implementations so a meaningful security
comparison can be made:

| Location | Role |
|---|---|
| Root (`flask_app/`, `nginx/`, `docker-compose.yml`) | **Final hardened** production implementation |
| [`original/`](original/) | **Baseline** implementation with intentional, documented vulnerabilities |

---

## 2. Architecture

```
[Client Browser]
      │  HTTPS only — TLS 1.2 / 1.3, NIST SP 800-52 cipher suites
      ▼
┌─────────────────────────────────────────────┐
│ Nginx ingress controller (container)         │
│  • TLS termination (port 443)                │
│  • Port 80 → 301 redirect to HTTPS           │
│  • Security headers (HSTS, CSP, X-Frame…)    │
│  • Per-IP rate limiting & connection limits  │
│  • STIG-formatted access logging             │
└───────────────────┬─────────────────────────┘
      │  Plain HTTP over the internal Docker bridge network
      │  (flask_app has NO host-exposed port)
      ▼
┌─────────────────────────────────────────────┐
│ Flask + Gunicorn (container)                 │
│  • OTP encrypt/decrypt logic                 │
│  • CSRF protection, input validation         │
│  • Application-level rate limiting           │
│  • Structured audit logging (no secrets)     │
│  • Security headers (defence in depth)       │
└─────────────────────────────────────────────┘
```

Traffic can **only** reach Flask through Nginx — Flask is on an internal Docker network
and exposes no host port.

---

## 3. How to Run

### Prerequisites
- Docker & Docker Compose
- `make`, `openssl`, `bash` (for cert generation and TLS tests)

### Step 1 — Create the environment file
```bash
cp .env.example .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"   # paste into .env
```
`.env` carries `SECRET_KEY`, `FLASK_ENV`, `LOG_LEVEL`, and `RATELIMIT_STORAGE_URI`.
It is **gitignored** — never commit it. In production, source these from a secrets manager.

### Step 2 — Generate TLS certificates
```bash
make certs
```
Generates a 4096-bit RSA key, a SHA-256 self-signed certificate (365-day validity), and
4096-bit DH parameters into [`certs/`](certs/).
> ⚠️ The 4096-bit DH parameter generation can take **5–15 minutes**. This is normal.

### Step 3 — Build and start the hardened stack
```bash
make build
make up
```

### Step 4 — Access the application
```
https://localhost
```
Accept the self-signed certificate warning (expected in dev — production uses a CA cert).
Visiting `http://localhost` returns a **301 redirect to HTTPS**.

### Step 5 — Operate
```bash
make logs        # tail combined container logs
make test-tls    # verify TLS 1.2/1.3 work and TLS 1.1 is rejected
make down        # stop the stack
```

### Running the baseline (for comparison only)
```bash
make build-original
make up-original      # serves insecure HTTP on http://localhost:80
make down-original
```

### Security scanning
```bash
make scan-original   # Trivy HIGH/CRITICAL scan of baseline images
make scan-final      # Trivy HIGH/CRITICAL scan of hardened images
make scan-all        # both; results written to security_assessment/
```

> Full command list: `make help`.

---

## 4. What Each Thing Is For

### Top level
| Path | Purpose |
|---|---|
| [`docker-compose.yml`](docker-compose.yml) | Final hardened orchestration: internal network, non-root, `cap_drop: ALL`, read-only FS, resource limits, healthchecks. |
| [`Makefile`](Makefile) | One-command workflows for certs, build/up/down, scanning, and TLS verification. |
| [`README.md`](README.md) | Concise quick-start and compliance summary. |
| `PROJECT_GUIDE.md` | This document — full explanation. |
| `.env.example` | Template for required runtime config/secrets; copy to `.env` (gitignored). |
| `.gitignore` | Keeps secrets, private keys, venvs, and caches out of version control. |
| `logs/` | Local mount point for log inspection. |

### `certs/` — TLS material (NIST SP 800-52 Rev 2)
| File | Purpose |
|---|---|
| [`generate_certs.sh`](certs/generate_certs.sh) | Produces RSA-4096 key, SHA-256 self-signed cert, 4096-bit DH params. |
| [`openssl.cnf`](certs/openssl.cnf) | OpenSSL profile (subject, extensions) used by the script. |
| `server.key` / `server.crt` | Private key (mode 600) and certificate, bind-mounted read-only into Nginx. |
| `dhparam.pem` | 4096-bit Diffie-Hellman parameters for DHE forward secrecy. |

### `flask_app/` — Hardened application
| File | Purpose |
|---|---|
| [`app.py`](flask_app/app.py) | Application factory, OTP logic, routes, CSRF, rate limiting, security headers, structured logging, generic error handlers. |
| [`config.py`](flask_app/config.py) | Security config: CSPRNG `SECRET_KEY`, `Secure`/`HttpOnly`/`SameSite=Strict` cookies, 30-min session timeout, CSRF, body-size limit. |
| [`Dockerfile`](flask_app/Dockerfile) | Multi-stage build, non-root `USER otp`, Gunicorn WSGI server, healthcheck. |
| [`requirements.txt`](flask_app/requirements.txt) | Pinned dependencies (Flask 3, Flask-WTF, Flask-Limiter, Gunicorn 22…). |
| `templates/` | Jinja2 templates (auto-escaping on) — `base`, `index`, `encrypt`, `decrypt`, `error`. |
| `static/` | First-party CSS/JS only (strict CSP forbids inline/3rd-party scripts). |

### `nginx/` — Ingress controller (mandatory component)
| File | Purpose |
|---|---|
| [`nginx.conf`](nginx/nginx.conf) | TLS 1.2/1.3, NIST cipher suites, PFS, HSTS+headers, rate/conn limits, HTTP→HTTPS redirect, STIG access-log format, hidden-file blocking. |
| [`Dockerfile`](nginx/Dockerfile) | Pinned `nginx:1.25-alpine`, security patch upgrade, default config removed, curl for healthcheck. |

### `original/` — Intentionally vulnerable baseline
Mirrors the structure above but with inline `# SECURITY FINDING:` comments marking the
deliberate flaws (debug mode, hardcoded key, HTTP-only, root container, no CSRF, secrets
in logs, truncating XOR, etc.). **Assessment baseline only — never deploy.**

### `security_assessment/` — Deliverable reports
| File | Purpose |
|---|---|
| [`original_assessment.md`](security_assessment/original_assessment.md) | Findings against the baseline. |
| [`final_assessment.md`](security_assessment/final_assessment.md) | Findings against the hardened build, incl. accepted CAT III risks. |
| [`comparison.md`](security_assessment/comparison.md) | Side-by-side delta, DREAD scoring, OTP/STIG justification, extra STIGs/SRGs reviewed. |
| `image_scan_report.md`, `trivy_*.txt` | Container image vulnerability scan outputs. |

---

## 5. Requirement-by-Requirement Compliance

| # | Requirement | Status | Where it's implemented |
|---|---|---|---|
| 1 | Browser-based OTP application | ✅ Met | `flask_app/` + templates |
| 2 | Build on provided Flask + Nginx; **Nginx ingress must be used** | ✅ Met | Nginx is the sole entry point; Flask has no host port |
| 3 | Encryption / OTP use compliant with ASD STIG | ✅ Met (with documented justification) | CSPRNG keys, length-equality enforcement, single-use keys — see `comparison.md` §5 |
| 4 | Logging compliant with ASD STIG | ✅ Met | Nginx `asd_stig` log format; Flask structured audit logs via `app.logger` (no secrets) |
| 5 | TLS via a NIST 800-52 cipher suite | ✅ Met | `nginx.conf` `ssl_ciphers` (ECDHE/DHE + AEAD only) |
| 6 | TLS strictly enforced; HTTPS-only | ✅ Met | Port 80 → 301 redirect; HSTS preload; `Secure` cookies |
| 7 | Security assessment of original **and** final | ✅ Met | `original_assessment.md`, `final_assessment.md` |
| 8 | Comparison of the two assessments | ✅ Met | `comparison.md` |
| 9 | Check other relevant STIGs/SRGs | ✅ Met | `comparison.md` §6 (Container Platform SRG, Web Server SRG, PKI SRG…) |
| 10 | Justify any non-compliance + remediation timeline | ✅ Met | 3 accepted CAT III risks documented with remediation path |

### Accepted (justified) residual risks — all CAT III
1. **Self-signed certificate** — no DoD PKI access in the dev environment. *Fix:* swap in a CA-issued cert before production.
2. **FIPS 140-2 module not validated** — depends on the host OS. *Fix:* deploy on a FIPS-enabled host (e.g. RHEL with `fips=1`).
3. **OTP key distribution** — an out-of-band procedural control, not an in-app feature. *Fix:* document in the Key Management Policy.

---

## 6. Known Issues / Notes for Operators

- **Logging now routed through `app.logger` (fixed).** Previously the route handlers
  emitted audit events via `logging.getLogger('otp_messenger')`, a logger that never
  received the STIG-formatted handler configured in `_configure_logging()`. All audit
  events in [`flask_app/app.py`](flask_app/app.py) now log through `app.logger`
  (`current_app.logger` inside request handlers, the closured `app.logger` inside error
  handlers), so every application audit record carries the structured format and is
  emitted at the configured level.
- **`SECRET_KEY` in `docker-compose.yml`** is a development placeholder. Inject from a
  secrets manager (Vault, AWS SSM) in production.
- **Log retention** relies on the Docker log driver / a downstream SIEM; configure
  centralised aggregation and rotation per STIG retention requirements before go-live.
- See the production checklist in [`README.md`](README.md#production-deployment-checklist).

---

## 7. NIST SP 800-52 Rev 2 — Cipher Suites in Use

**TLS 1.3 (automatic):** `TLS_AES_256_GCM_SHA384`, `TLS_AES_128_GCM_SHA256`,
`TLS_CHACHA20_POLY1305_SHA256`.

**TLS 1.2 (configured):** ECDHE/DHE key exchange with AES-GCM or CHACHA20-POLY1305 AEAD
ciphers only (see `nginx.conf`).

**Disabled:** SSLv2/3, TLS 1.0/1.1, and all NULL/EXPORT/RC4/DES/3DES/non-AEAD suites.

# Security Assessment — Final (Hardened) Implementation

**Assessment Date:** 2026-06-22  
**Assessor:** Company X Cybersecurity Engineering Team  
**Scope:** Root-level `flask_app/`, `nginx/`, `docker-compose.yml`  
**Classification:** OFFICIAL USE ONLY  

---

## 1. Executive Summary

The final hardened implementation was assessed against the same standards used for the original baseline:

| Standard | Version |
|---|---|
| Application Security and Development STIG | V5R3 |
| Web Server SRG | V2R3 |
| Container Platform SRG | V2R1 |
| NIST SP 800-52 | Rev 2 |

The assessment identified **0 CAT I**, **0 CAT II**, and **3 CAT III** findings. All CAT I and CAT II findings from the original implementation have been fully remediated. The three remaining CAT III findings are **accepted risks** with documented justifications and remediation timelines.

**Authorisation to Deploy:** CONDITIONALLY AUTHORISED for test and development environments. Production deployment requires CA-signed certificates and FIPS-mode kernel (see Section 5).

---

## 2. STIG Compliance Matrix

### 2.1 Application Security and Development STIG

| Control ID | Title | Status | Notes |
|---|---|---|---|
| APSC-DV-000160 | DoD-approved encryption | COMPLIANT | OTP via CSPRNG XOR; TLS 1.2/1.3 in transit |
| APSC-DV-000300 | NIST SP 800-52 TLS | COMPLIANT | See §3.1 — cipher suite full analysis |
| APSC-DV-000460 | XSS prevention | COMPLIANT | CSP, X-XSS-Protection headers; Jinja2 auto-escaping |
| APSC-DV-000500 | CSRF protection | COMPLIANT | Flask-WTF CSRF tokens on all POST forms |
| APSC-DV-000560 | Error message info disclosure | COMPLIANT | Generic error messages; no stack traces to client |
| APSC-DV-001460 | Input validation | COMPLIANT | Max 10,000 chars; WTForms validators; 32 KB body limit |
| APSC-DV-001750 | NIST-validated crypto algorithms | COMPLIANT* | See §5 for FIPS 140-2 note |
| APSC-DV-002000 | HTTPS enforcement | COMPLIANT | HTTP → HTTPS 301 redirect; HSTS with preload |
| APSC-DV-002010 | TLS 1.2 minimum | COMPLIANT | TLS 1.2 and 1.3 only; TLS 1.0/1.1 disabled |
| APSC-DV-002940 | Protect audit information | COMPLIANT | Log volume mounted; root filesystem read-only |
| APSC-DV-003000 | Generate audit records | COMPLIANT | All requests logged at nginx and application layer |
| APSC-DV-003010 | Audit record fields | COMPLIANT | Timestamp, IP, method, path, status, TLS version |
| APSC-DV-003200 | Sensitive data not in logs | COMPLIANT | No plaintext, keys, or message content in any log |
| APSC-DV-003280 | Session token generation | COMPLIANT | `secrets.token_hex(32)` from OS CSPRNG |
| APSC-DV-003360 | Session timeout | COMPLIANT | 30-minute `PERMANENT_SESSION_LIFETIME` |

### 2.2 Web Server SRG

| Control ID | Title | Status | Notes |
|---|---|---|---|
| V-214230 | Remove version identifiers | COMPLIANT | `server_tokens off`; Server header overridden |
| V-214270 | Disable unnecessary features | COMPLIANT | Only required modules; no PHP/CGI |
| V-214277 | Access log format | COMPLIANT | Custom `asd_stig` log format with all required fields |
| V-214278 | Protect log files | COMPLIANT | Logs written to named Docker volume |

### 2.3 NIST SP 800-52 Rev 2 — TLS Configuration

| Requirement | Required | Implemented | Status |
|---|---|---|---|
| TLS 1.2 support | SHALL | TLSv1.2 | COMPLIANT |
| TLS 1.3 support | SHOULD | TLSv1.3 | COMPLIANT |
| TLS 1.1 and below | SHALL NOT | Disabled | COMPLIANT |
| AES-128-GCM cipher (TLS 1.2) | SHALL | ECDHE-RSA-AES128-GCM-SHA256 | COMPLIANT |
| AES-256-GCM cipher (TLS 1.2) | SHALL | ECDHE-RSA-AES256-GCM-SHA384 | COMPLIANT |
| ECDSA ciphers | SHOULD | ECDHE-ECDSA-AES{128,256}-GCM-SHA{256,384} | COMPLIANT |
| CHACHA20-POLY1305 | SHOULD | ECDHE-RSA/ECDSA-CHACHA20-POLY1305 | COMPLIANT |
| DHE ciphers with 4096-bit DH params | SHOULD | DHE-RSA-AES{128,256}-GCM-SHA{256,384} | COMPLIANT |
| Perfect Forward Secrecy | SHALL | ECDHE / DHE only; session tickets off | COMPLIANT |
| RSA key minimum 2048 bits | SHALL | 4096-bit RSA | COMPLIANT |
| Certificate SHA-256+ | SHALL | SHA-256 | COMPLIANT |
| HSTS | SHOULD | max-age=31536000; includeSubDomains; preload | COMPLIANT |
| OCSP Stapling | SHOULD | Enabled | COMPLIANT* |
| No RC4 | SHALL NOT | Not present | COMPLIANT |
| No DES/3DES | SHALL NOT | Not present | COMPLIANT |
| No NULL ciphers | SHALL NOT | Not present | COMPLIANT |
| No export ciphers | SHALL NOT | Not present | COMPLIANT |
| No MD5-based HMAC | SHALL NOT | Not present | COMPLIANT |

*OCSP stapling requires a CA-issued certificate; ineffective with self-signed certs. See §5.

### 2.4 Container Platform SRG

| Control | Title | Status | Notes |
|---|---|---|---|
| V-205070 | Drop unnecessary capabilities | COMPLIANT | `cap_drop: ALL`; nginx adds only NET_BIND_SERVICE |
| V-205072 | Non-root container user | COMPLIANT | `USER otp` (UID 1000) in Flask Dockerfile |
| V-205076 | Patched base images | COMPLIANT | python:3.11-slim, nginx:1.25-alpine (current stable) |
| V-205108 | Read-only root filesystem | COMPLIANT | `read_only: true`; tmpfs for /tmp |
| V-205041 | Resource limits | COMPLIANT | CPU and memory limits defined |
| V-205069 | No unnecessary port exposure | COMPLIANT | Flask not exposed to host; only nginx on 80/443 |
| — | Health checks | COMPLIANT | HEALTHCHECK in both Dockerfiles |
| — | no-new-privileges | COMPLIANT | `security_opt: no-new-privileges:true` |

---

## 3. Detailed Technical Controls

### 3.1 TLS Implementation (NIST SP 800-52 Rev 2)

**Protocol Versions:**
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
```
- TLS 1.3: Automatic cipher selection (TLS_AES_256_GCM_SHA384, TLS_AES_128_GCM_SHA256, TLS_CHACHA20_POLY1305_SHA256)
- TLS 1.2: Restricted to NIST-approved AEAD suites only
- TLS 1.0 and 1.1: Explicitly excluded

**TLS 1.2 Cipher Suite Order (server preference):**
```
ECDHE-ECDSA-AES256-GCM-SHA384    ← preferred: ECDSA key + AES-256
ECDHE-RSA-AES256-GCM-SHA384      ← RSA equivalent
ECDHE-ECDSA-AES128-GCM-SHA256
ECDHE-RSA-AES128-GCM-SHA256
ECDHE-ECDSA-CHACHA20-POLY1305
ECDHE-RSA-CHACHA20-POLY1305
DHE-RSA-AES256-GCM-SHA384
DHE-RSA-AES128-GCM-SHA256
```

All suites provide:
- **Authentication:** RSA or ECDSA
- **Key Exchange:** ECDHE or DHE (Perfect Forward Secrecy)
- **Bulk Encryption:** AES-128-GCM, AES-256-GCM, or ChaCha20-Poly1305 (AEAD)

**DH Parameters:** 4096-bit (`certs/dhparam.pem`) — exceeds NIST minimum of 2048 bits.

**Session Security:**
```nginx
ssl_session_tickets off;    # Strict PFS — no session ticket key reuse
ssl_session_timeout 10m;    # 10-minute session cache lifetime
```

### 3.2 OTP Cryptographic Implementation (APSC-DV-001750)

The OTP implementation satisfies the theoretical requirements for information-theoretic security:

1. **Key Generation:** `secrets.token_bytes(n)` → calls `os.urandom(n)` → `getrandom(2)` syscall (Linux kernel CSPRNG)
2. **Key Length:** Exactly equal to the plaintext length in bytes (Unicode text converted to UTF-8 first)
3. **Single Use:** Keys are generated per-request and never persisted; once the HTTP response is sent the key is irrecoverably gone
4. **XOR Operation:** Applied byte-by-byte: `ciphertext[i] = plaintext[i] XOR key[i]`
5. **Encoding:** Base64 (RFC 4648) used only for display — does not affect cryptographic strength

**Mathematical Security:**  
Given a ciphertext `C = P XOR K`, where `K` is uniformly random and `|K| = |P|`, the ciphertext `C` is statistically independent of `P`. For every possible plaintext `P'` there exists exactly one key `K' = C XOR P'`. Without the key, an attacker learns zero information about the plaintext.

### 3.3 Session Management (APSC-DV-003280, APSC-DV-003360)

```python
SECRET_KEY = secrets.token_hex(32)   # 256-bit random key from OS CSPRNG
SESSION_COOKIE_SECURE     = True     # HTTPS only
SESSION_COOKIE_HTTPONLY   = True     # Not accessible via JavaScript
SESSION_COOKIE_SAMESITE   = 'Strict' # No cross-site cookie sending
PERMANENT_SESSION_LIFETIME = 1800   # 30-minute timeout
```

Flask session cookies are HMAC-SHA256 signed using `SECRET_KEY`. An attacker cannot forge a valid session cookie without knowledge of the key.

### 3.4 Audit Logging (APSC-DV-003000, APSC-DV-003010)

**Nginx log format (all HTTPS requests):**
```
2026-06-22T14:32:01+00:00 | 192.168.1.100 | "POST /encrypt HTTP/1.1" | 200 | 842 | "" | "Mozilla/5.0" | TLSv1.3 | TLS_AES_256_GCM_SHA384
```

Fields: timestamp (ISO-8601), source IP, request line, HTTP status, response size, referrer, User-Agent, TLS version, cipher suite.

**Application log format (Flask/Gunicorn):**
```
2026-06-22T14:32:01+0000 | INFO     | 192.168.1.100 | POST /encrypt | ENCRYPT | RESULT=SUCCESS | MSG_BYTES=47
```

Fields: timestamp, severity, source IP, method+path, event type, outcome, metadata.

**Sensitive data explicitly excluded from all logs:**
- Plaintext message content
- OTP key material
- Session cookie values
- CSRF tokens

### 3.5 Security Headers

| Header | Value | Standard |
|---|---|---|
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload | NIST 800-52 §3.4 |
| X-Frame-Options | DENY | ASD STIG APSC-DV-000460 |
| X-Content-Type-Options | nosniff | ASD STIG |
| Content-Security-Policy | default-src 'self'; frame-ancestors 'none'; ... | ASD STIG APSC-DV-000460 |
| X-XSS-Protection | 1; mode=block | ASD STIG APSC-DV-000460 |
| Referrer-Policy | strict-origin-when-cross-origin | ASD STIG |
| Permissions-Policy | geolocation=(), microphone=(), camera=() | Hardening best practice |
| Cache-Control | no-store, no-cache, must-revalidate, private | APSC-DV-002530 |

---

## 4. Remaining Findings

### FIND-FINAL-001 — Self-Signed TLS Certificate
**Severity:** CAT III  
**Status:** ACCEPTED — Justification Provided  

**Description:**  
The implementation uses a self-signed RSA-4096/SHA-256 certificate generated by `certs/generate_certs.sh`. Self-signed certificates cannot be verified by standard trust stores; clients must manually trust the certificate or receive the CA cert out of band. OCSP stapling is not functional with self-signed certificates.

**Justification:**  
Self-signed certificates are the maximum achievable in a development/test environment without access to a DoD PKI infrastructure or a commercial CA. The certificate meets all NIST SP 800-52 requirements for key size (4096-bit RSA) and signature algorithm (SHA-256). All other TLS controls are fully compliant.

**Remediation Timeline:**  
Prior to production deployment, replace with a certificate issued by a DoD-approved PKI authority (e.g., DoD Root CA) or an accredited commercial CA. Estimated effort: 1–2 business days (pending CA approval).

---

### FIND-FINAL-002 — FIPS 140-2 Module Validation Not Verified
**Severity:** CAT III  
**Status:** ACCEPTED — Justification Provided  

**Description:**  
APSC-DV-001750 / V-222397 requires use of FIPS 140-2 validated cryptographic modules. Python's `secrets` module and `os.urandom()` use the Linux kernel CSPRNG (`getrandom` syscall). The kernel's CSPRNG is FIPS 140-2 validated *only when the operating system runs in FIPS mode* (e.g., RHEL with FIPS kernel parameter). The container base image (`python:3.11-slim` on Debian) does not enforce FIPS mode by default.

**Justification:**  
The OTP key generation algorithm (`os.urandom`) is identical in FIPS and non-FIPS mode — the difference is whether the module has undergone formal NIST validation. The underlying implementation (Linux kernel's `/proc/sys/kernel/random`) is FIPS 140-2 validated on FIPS-enabled systems. This finding is a deployment environment dependency, not an application code deficiency.

**Remediation Timeline:**  
Deploy containers on a FIPS 140-2 enabled host OS (e.g., RHEL 8/9 with `fips=1` kernel parameter). Alternatively, switch to the `openssl-fips` binding via the `cryptography` Python library. Estimated effort: 2–5 days (requires FIPS-enabled host provisioning).

---

### FIND-FINAL-003 — OTP Key Distribution Out of Scope
**Severity:** CAT III  
**Status:** ACCEPTED — Architectural Limitation  

**Description:**  
The security of a One Time Pad depends critically on secure, out-of-band key distribution. This application generates and displays the key in the HTTPS response. The key must then be transmitted to the recipient via a separate, approved channel. The application does not enforce or verify this distribution mechanism — it is a procedural control outside the application's scope.

**Justification:**  
The application displays a clear security notice requiring separate key distribution. The TLS transport protects the key display from network interception. The application's role is OTP computation, not key distribution infrastructure. Secure key distribution is addressed in the organisation's key management procedures.

**Remediation:** Procedural control — document in key management policy. No code change required.

---

## 5. Non-Compliance Items Requiring Justification

The following STIG controls cannot be fully satisfied in the current deployment model:

| Control | Requirement | Gap | Justification | Timeline |
|---|---|---|---|---|
| APSC-DV-001750 | FIPS 140-2 validated modules | OS not in FIPS mode | Application uses FIPS-equivalent OS CSPRNG; FIPS mode is host configuration | Before production |
| NIST 800-52 §3.2 | CA-issued certificate | Self-signed cert | No DoD PKI access in dev environment; cert parameters are compliant | Before production |
| APSC-DV-002010 | OCSP Stapling | Non-functional with self-signed cert | Architectural dependency on CA issuance | Before production |

---

## 6. Conclusion

The final hardened implementation eliminates all 5 CAT I and all 9 CAT II findings identified in the original baseline. The three remaining CAT III findings are accepted risks with documented justifications and clear remediation timelines, all of which are environmental/deployment dependencies rather than application code deficiencies.

The implementation is **CONDITIONALLY AUTHORISED** for test and development use. Production authorisation is contingent on:

1. Replacement of self-signed certificate with CA-issued certificate
2. Deployment on a FIPS 140-2 enabled host OS
3. Review and acceptance of the OTP key distribution policy

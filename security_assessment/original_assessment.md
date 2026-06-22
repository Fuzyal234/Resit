# Security Assessment — Original (Baseline) Implementation

**Assessment Date:** 2026-06-22  
**Assessor:** Company X Cybersecurity Engineering Team  
**Scope:** `original/` directory — Flask application and Nginx ingress controller  
**Classification:** OFFICIAL USE ONLY  

---

## 1. Executive Summary

The original implementation of the OTP Messenger was assessed against the following standards:

| Standard | Version |
|---|---|
| Application Security and Development STIG | V5R3 |
| Web Server SRG | V2R3 |
| Container Platform SRG | V2R1 |
| NIST SP 800-52 | Rev 2 |

The assessment identified **17 findings**: **5 CAT I (Critical)**, **9 CAT II (High)**, and **3 CAT III (Low)**. The original implementation does not meet the minimum security baseline for any of the referenced standards. Deployment to any environment is **NOT AUTHORISED** without remediation.

---

## 2. Methodology

- Manual source code review of `original/flask_app/app.py`
- Dockerfile analysis
- Nginx configuration review against NIST SP 800-52 Rev 2 and Web Server SRG
- Docker Compose file review against Container Platform SRG
- Dependency analysis of `requirements.txt`

---

## 3. Findings

### 3.1 CAT I Findings (Critical)

---

#### FIND-ORIG-001 — Debug Mode Enabled in Production
**Severity:** CAT I  
**STIG Control:** APSC-DV-002530 / V-222544  
**Standard:** ASD STIG  

**Description:**  
The Flask application is started with `app.run(debug=True, host='0.0.0.0', port=5000)`. When `debug=True` is active, Flask enables the Werkzeug interactive debugger. If an unhandled exception occurs, the debugger is rendered in the browser and allows arbitrary Python code execution via a PIN-protected console. This is effectively **Remote Code Execution (RCE)** if the PIN is weak or leaked.

**Evidence:**
```python
# original/flask_app/app.py, line 52
app.run(debug=True, host='0.0.0.0', port=5000)
```
```yaml
# original/docker-compose.yml
environment:
  - FLASK_DEBUG=1
```

**Risk:** Complete application and host compromise.  
**Status:** OPEN — Not remediated in original implementation.

---

#### FIND-ORIG-002 — Hardcoded Cryptographic Secret Key
**Severity:** CAT I  
**STIG Control:** APSC-DV-003280 / V-222400  
**Standard:** ASD STIG  

**Description:**  
The Flask `secret_key` is hardcoded as `'supersecretkey123'`. This value is committed to source control and is therefore effectively public. It is used to sign session cookies and CSRF tokens. An attacker with knowledge of this value can forge valid session cookies, impersonate any user, and bypass CSRF protections.

**Evidence:**
```python
# original/flask_app/app.py, line 17
app.secret_key = 'supersecretkey123'
```

**Risk:** Session forgery, privilege escalation.  
**Status:** OPEN.

---

#### FIND-ORIG-003 — No Transport Layer Security (HTTPS Not Enforced)
**Severity:** CAT I  
**STIG Control:** APSC-DV-002000 / V-222596  
**Standard:** ASD STIG, NIST SP 800-52 Rev 2  

**Description:**  
The Nginx configuration listens only on port 80 (plain HTTP). All traffic — including plaintext messages, OTP keys, and session cookies — is transmitted in cleartext. Any network adversary can capture, read, and modify all application data in transit.

**Evidence:**
```nginx
# original/nginx/nginx.conf, line 13
listen 80;
# No TLS block exists
```

**Risk:** Confidentiality and integrity loss of all OTP keys and messages; credential theft.  
**Status:** OPEN.

---

#### FIND-ORIG-004 — Flask Application Port Directly Exposed to Host
**Severity:** CAT I  
**STIG Control:** Container Platform SRG V-205069  
**Standard:** Container Platform SRG  

**Description:**  
`docker-compose.yml` maps port 5000 of the `flask_app` container directly to the host: `ports: - "5000:5000"`. This bypasses Nginx entirely, exposing the Flask development server directly to the network with no TLS, no rate limiting, and no security headers.

**Evidence:**
```yaml
# original/docker-compose.yml
services:
  flask_app:
    ports:
      - "5000:5000"
```

**Risk:** Direct exploitation of the Flask development server; bypasses all ingress controls.  
**Status:** OPEN.

---

#### FIND-ORIG-005 — Container Running as Root
**Severity:** CAT I  
**STIG Control:** Container Platform SRG V-205072  
**Standard:** Container Platform SRG  

**Description:**  
The `original/flask_app/Dockerfile` does not create or switch to a non-root user. The application process runs as UID 0 (root) inside the container. If the application is compromised, the attacker obtains root within the container namespace, significantly easing container escape.

**Evidence:**
```dockerfile
# original/flask_app/Dockerfile — no USER directive
FROM python:3.9
WORKDIR /app
CMD ["python", "app.py"]
```

**Risk:** Privilege escalation and container escape.  
**Status:** OPEN.

---

### 3.2 CAT II Findings (High)

---

#### FIND-ORIG-006 — No CSRF Protection
**Severity:** CAT II  
**STIG Control:** APSC-DV-000500 / V-222450  
**Standard:** ASD STIG  

**Description:**  
Neither the `/encrypt` nor `/decrypt` endpoints implement Cross-Site Request Forgery (CSRF) protection. A malicious web page can submit forms to these endpoints on behalf of an authenticated user.

**Evidence:** No `flask_wtf` or equivalent CSRF library in `requirements.txt`; no CSRF token in HTML forms.

**Status:** OPEN.

---

#### FIND-ORIG-007 — Sensitive Data Written to Logs
**Severity:** CAT II  
**STIG Control:** APSC-DV-003200 / V-222406  
**Standard:** ASD STIG  

**Description:**  
The `otp_encrypt()` and `otp_decrypt()` functions write plaintext message content to the application log using `logger.debug()`. Logging plaintext OTP material violates the fundamental requirement that log files must not contain sensitive data.

**Evidence:**
```python
# original/flask_app/app.py, lines 25, 33
logger.debug(f"Encrypted message: '{plaintext}' -> ciphertext: {ct_b64}")
logger.debug(f"Decrypted message: '{decoded}'")
```

**Status:** OPEN.

---

#### FIND-ORIG-008 — Verbose Exception Messages Exposed to User
**Severity:** CAT II  
**STIG Control:** APSC-DV-000560 / V-222480  
**Standard:** ASD STIG  

**Description:**  
The `/decrypt` route returns the raw Python exception string to the HTTP response body: `return f"Error decrypting: {str(e)}", 400`. This can expose internal stack traces, module paths, and application logic to attackers.

**Evidence:**
```python
# original/flask_app/app.py, line 48
return f"Error decrypting: {str(e)}", 400
```

**Status:** OPEN.

---

#### FIND-ORIG-009 — No Input Length Validation
**Severity:** CAT II  
**STIG Control:** APSC-DV-001460 / V-222396 (input validation)  
**Standard:** ASD STIG  

**Description:**  
There is no maximum length enforced on the `message`, `ciphertext`, or `key` form fields. An attacker can submit arbitrarily large payloads, consuming excessive server memory and CPU during OTP operations.

**Status:** OPEN.

---

#### FIND-ORIG-010 — No Rate Limiting
**Severity:** CAT II  
**STIG Control:** APSC-DV-001460 / V-222396  
**Standard:** ASD STIG  

**Description:**  
No rate limiting is applied at either the Nginx or Flask layer. The application is vulnerable to brute-force and denial-of-service attacks.

**Status:** OPEN.

---

#### FIND-ORIG-011 — No Security Response Headers
**Severity:** CAT II  
**STIG Control:** APSC-DV-000460 / V-222460 (XSS), APSC-DV-000500 / V-222450 (clickjacking)  
**Standard:** ASD STIG  

**Description:**  
The application returns no security-related HTTP headers: no `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, or `Referrer-Policy`. The application is vulnerable to clickjacking and reflected XSS.

**Status:** OPEN.

---

#### FIND-ORIG-012 — Nginx Version Disclosure
**Severity:** CAT II  
**STIG Control:** Web Server SRG V-214230  
**Standard:** Web Server SRG  

**Description:**  
`server_tokens` is not disabled in `nginx.conf`. Nginx includes its version in the `Server` response header and in error pages, aiding attacker reconnaissance.

**Evidence:**
```nginx
# original/nginx/nginx.conf — no server_tokens directive
```

**Status:** OPEN.

---

#### FIND-ORIG-013 — Outdated Base Images with Known CVEs
**Severity:** CAT II  
**STIG Control:** Container Platform SRG V-205076  
**Standard:** Container Platform SRG  

**Description:**  
`python:3.9` (full image, ~900MB) and `nginx:1.21` are significantly outdated. Python 3.9 has received no security updates since October 2025. Nginx 1.21 has multiple published CVEs. The full Python image includes build tools and many packages with known vulnerabilities not present in a slim/alpine variant.

**Status:** OPEN.

---

#### FIND-ORIG-014 — No Container Capability Restrictions
**Severity:** CAT II  
**STIG Control:** Container Platform SRG V-205070  
**Standard:** Container Platform SRG  

**Description:**  
Neither the `flask_app` nor `nginx` services drop Linux capabilities in `docker-compose.yml`. By default, Docker grants a broad set of capabilities including `CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `NET_RAW`, and others that should be removed from application containers.

**Status:** OPEN.

---

### 3.3 CAT III Findings (Low)

---

#### FIND-ORIG-015 — Unstructured Logging Format
**Severity:** CAT III  
**STIG Control:** APSC-DV-003010 / V-222432  
**Standard:** ASD STIG  

**Description:**  
The logging configuration uses `basicConfig` with no structured format. Log entries lack required fields: source IP address, request method, path, and event outcome, making audit trail analysis difficult.

**Status:** OPEN.

---

#### FIND-ORIG-016 — No Resource Limits on Containers
**Severity:** CAT III  
**STIG Control:** Container Platform SRG V-205041  
**Standard:** Container Platform SRG  

**Description:**  
No CPU or memory limits are set on either service. A compromised or misbehaving container can consume all available host resources.

**Status:** OPEN.

---

#### FIND-ORIG-017 — No Health Checks Defined
**Severity:** CAT III  
**STIG Control:** Container Platform SRG (availability controls)  
**Standard:** Container Platform SRG  

**Description:**  
No `HEALTHCHECK` instruction is defined in either Dockerfile, and no health check is configured in `docker-compose.yml`. Container orchestrators cannot determine whether the application is healthy.

**Status:** OPEN.

---

## 4. Summary Table

| ID | Title | Severity | STIG Control | Status |
|---|---|---|---|---|
| FIND-ORIG-001 | Debug mode enabled | CAT I | APSC-DV-002530 | OPEN |
| FIND-ORIG-002 | Hardcoded secret key | CAT I | APSC-DV-003280 | OPEN |
| FIND-ORIG-003 | No TLS (HTTP only) | CAT I | APSC-DV-002000 | OPEN |
| FIND-ORIG-004 | Flask port exposed to host | CAT I | Container SRG V-205069 | OPEN |
| FIND-ORIG-005 | Container runs as root | CAT I | Container SRG V-205072 | OPEN |
| FIND-ORIG-006 | No CSRF protection | CAT II | APSC-DV-000500 | OPEN |
| FIND-ORIG-007 | Sensitive data in logs | CAT II | APSC-DV-003200 | OPEN |
| FIND-ORIG-008 | Verbose error messages | CAT II | APSC-DV-000560 | OPEN |
| FIND-ORIG-009 | No input length validation | CAT II | APSC-DV-001460 | OPEN |
| FIND-ORIG-010 | No rate limiting | CAT II | APSC-DV-001460 | OPEN |
| FIND-ORIG-011 | No security headers | CAT II | APSC-DV-000460 | OPEN |
| FIND-ORIG-012 | Nginx version disclosure | CAT II | Web SRG V-214230 | OPEN |
| FIND-ORIG-013 | Outdated base images | CAT II | Container SRG V-205076 | OPEN |
| FIND-ORIG-014 | No capability restrictions | CAT II | Container SRG V-205070 | OPEN |
| FIND-ORIG-015 | Unstructured logging | CAT III | APSC-DV-003010 | OPEN |
| FIND-ORIG-016 | No container resource limits | CAT III | Container SRG V-205041 | OPEN |
| FIND-ORIG-017 | No health checks | CAT III | Container SRG (availability) | OPEN |

**Total: 5 CAT I | 9 CAT II | 3 CAT III**

---

## 5. Conclusion

The original implementation fails to meet the minimum security requirements of the ASD STIG, NIST SP 800-52 Rev 2, and the Container Platform SRG. The five CAT I findings alone represent critical, immediately exploitable vulnerabilities. **This implementation must not be deployed to any environment.**

All 17 findings have been remediated in the final hardened implementation. See `final_assessment.md` and `comparison.md`.

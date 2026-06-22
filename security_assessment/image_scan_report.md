# Image Vulnerability Scan Report

**Scan Date:** 2026-06-22  
**Tool:** Trivy (aquasec/trivy:latest)  
**Scope:** HIGH and CRITICAL severity CVEs  
**Images Scanned:** 4 (2 original, 2 final)  
**Classification:** OFFICIAL USE ONLY  

Raw scan output files:
- `trivy_original_flask.txt` — original Flask image
- `trivy_original_nginx.txt` — original Nginx image
- `trivy_final_flask.txt` — final Flask image (post-remediation)
- `trivy_final_nginx.txt` — final Nginx image (post-remediation)

---

## 1. Scan Summary

| Image | Base OS | HIGH | CRITICAL | Total |
|---|---|---|---|---|
| `otp-original-flask:latest` | debian 13.1 (python:3.9) | 1,029 | 190 | **1,219** |
| `otp-original-nginx:latest` | debian 11.3 (nginx:1.21) | 156 | 28 | **184** |
| `otp-flask:latest` (final) | debian 13.5 (python:3.11-slim) | 12 | 2 | **14** |
| `otp-nginx:latest` (final) | alpine 3.19.1 (nginx:1.25-alpine + apk upgrade) | 0 | 0 | **0** |

**Aggregate reduction: 1,403 → 14 vulnerabilities (−99.0%)**

---

## 2. Original Images

### 2.1 `otp-original-flask:latest` (python:3.9, full Debian)

**Total: 1,219 HIGH/CRITICAL**

The full `python:3.9` base image ships with a complete Debian 11 toolchain including ImageMagick, GnuTLS, libgnutls, libfreetype, build tools, and hundreds of packages with no relation to the application. This inflated attack surface is the primary driver of the high CVE count.

**Representative CRITICAL CVEs:**

| CVE | Package | Description |
|---|---|---|
| CVE-2026-22770 | imagemagick (×8 variants) | DoS via improper input validation |
| CVE-2026-33845 | libgnutls30 | DoS via DTLS zero-length fragment |
| CVE-2025-14087 | libglib2.0 | Buffer underflow in GVariant parser |
| CVE-2024-37371 | libkrb5 / libgssapi | GSS message token handling |
| CVE-2022-37434 | zlib1g | Heap buffer overflow in inflate() |
| CVE-2026-42496 | perl-base | Path traversal in Archive::Tar |

**Root cause:** `python:3.9` (full image) is ~900 MB and includes hundreds of packages that are irrelevant to the application. None of these packages are used by the OTP Messenger application.

### 2.2 `otp-original-nginx:latest` (nginx:1.21, Debian 11)

**Total: 184 HIGH/CRITICAL**

nginx:1.21 is an end-of-life release. Debian 11 (bullseye) packages bundled in this image have accumulated over three years of unpatched CVEs.

**Representative CRITICAL CVEs:**

| CVE | Package | Description |
|---|---|---|
| CVE-2021-22945 | curl / libcurl4 | Use-after-free and double-free in MQTT |
| CVE-2019-8457 | libdb5.3 | Heap OOB read in rtreenode() |
| CVE-2022-27404 | libfreetype6 | Buffer overflow in sfnt_init_face |
| CVE-2026-33845 | libgnutls30 | DoS via DTLS zero-length fragment |
| CVE-2024-37371 | libkrb5 | GSS message token handling |
| CVE-2022-37434 | zlib1g | Heap buffer overflow in inflate() |
| CVE-2024-56171 | libxml2 | Use-After-Free in libxml2 |
| CVE-2026-42496 | perl-base | Path traversal in Archive::Tar |
| CVE-2022-1586 | libpcre2-8-0 | OOB read in compile_xclass_matchingpath |
| CVE-2021-46848 | libtasn1-6 | OOB access in ETYPE_OK |

---

## 3. Final Hardened Images

### 3.1 `otp-flask:latest` (python:3.11-slim, Debian 13.5)

**Total: 14 HIGH/CRITICAL (12 HIGH, 2 CRITICAL)**

The multi-stage Dockerfile using `python:3.11-slim` eliminates build tools, compilers, and most system libraries. The 14 remaining findings are all in packages that Debian ships as part of its minimal base and for which either:
- No fix is available yet (`fix_deferred` / `affected` status), or
- The fix is in a package update that Debian has not yet backported to stable

**Remaining CRITICAL CVEs:**

| CVE | Package | Status | Fix Available | Description |
|---|---|---|---|---|
| CVE-2026-42496 | perl-base | `fix_deferred` | No | perl-archive-tar: Path traversal — no upstream fix |
| CVE-2026-42497 | perl-base | `fix_deferred` | No | perl-Archive-Tar: Arbitrary file write |

**Remaining HIGH CVEs (selected):**

| CVE | Package | Status | Fix Available | Description |
|---|---|---|---|---|
| CVE-2025-69720 | libncursesw6 | `affected` | No | Buffer overflow in ncurses |
| CVE-2026-42497 | perl-base | `fix_deferred` | No | Arbitrary file write via Archive::Tar |

**Action taken during this assessment:**  
CVE-2024-1135 (gunicorn: HTTP Request Smuggling, HIGH, `fixed` in 22.0.0) was identified in the initial scan and remediated by upgrading `gunicorn==21.2.0` → `gunicorn==22.0.0` in `flask_app/requirements.txt`. The finding no longer appears in the post-remediation scan.

**Residual risk assessment:**  
- `perl-base` is a Debian system package required by `dpkg`. It cannot be removed without breaking the package manager. The CVEs are `fix_deferred` — Debian is aware but has not yet published a fix.
- `libncursesw6` has no fix available from Debian stable.
- These packages are not reachable by the OTP application's code path. The attack vector requires local system access, not a web request.
- **Risk: LOW** — no exploitable path via the web application surface.

### 3.2 `otp-nginx:latest` (nginx:1.25-alpine + apk upgrade)

**Total: 0 HIGH/CRITICAL**

The initial scan of this image (before remediation) found 20 HIGH/CRITICAL CVEs in `libexpat`, `libxml2`, and `curl` packages shipped with `alpine:3.19`. All were remediated by adding `apk upgrade --no-cache` to the Dockerfile, which installs the latest patched package versions from Alpine's security repository.

**CVEs remediated by `apk upgrade`:**

| CVE | Package | Severity | Fixed In |
|---|---|---|---|
| CVE-2024-45491 | libexpat | CRITICAL | 2.6.3-r0 |
| CVE-2024-45492 | libexpat | HIGH | 2.6.3-r0 |
| CVE-2024-45490 | libexpat | HIGH | 2.6.3-r0 |
| CVE-2024-56171 | libxml2 | CRITICAL | 2.11.8-r1 |
| CVE-2025-24928 | libxml2 | HIGH | 2.11.8-r1 |
| CVE-2024-6197 | curl | HIGH | 8.9.0-r0 |
| + 14 others | various | HIGH | — |

Post-remediation Trivy reports **0 vulnerabilities** for this image.

> **Note:** Alpine 3.19 has reached end-of-life. The `apk upgrade` patches all current CVEs using Alpine's security mirror, but future upstream fixes may not be backported to 3.19. **Remediation timeline:** Update base image to `nginx:1.25-alpine3.20` or the current Alpine LTS in the next scheduled maintenance window. Estimated effort: < 1 day.

---

## 4. Comparison Table

| Metric | Original | Final | Reduction |
|---|---|---|---|
| Flask image — CRITICAL | 190 | 2 | −98.9% |
| Flask image — HIGH | 1,029 | 12 | −98.8% |
| Flask image — TOTAL | **1,219** | **14** | **−98.9%** |
| Nginx image — CRITICAL | 28 | 0 | −100% |
| Nginx image — HIGH | 156 | 0 | −100% |
| Nginx image — TOTAL | **184** | **0** | **−100%** |
| **Combined TOTAL** | **1,403** | **14** | **−99.0%** |

---

## 5. Residual Risk Register (Image CVEs)

| Finding | Image | CVE | Severity | Status | Justification | Timeline |
|---|---|---|---|---|---|---|
| perl-base path traversal | Flask | CVE-2026-42496 | CRITICAL | fix_deferred | System package, no fix available; not reachable via web interface | Apply when Debian releases fix |
| perl-base arbitrary write | Flask | CVE-2026-42497 | HIGH | fix_deferred | Same package as above; same justification | Apply when Debian releases fix |
| libncursesw6 buffer overflow | Flask | CVE-2025-69720 | HIGH | affected | Terminal library not used by application; no fix available | Apply when Debian releases fix |
| Alpine 3.19 EOL | Nginx | — | — | Architecture | All current CVEs patched via `apk upgrade`; future CVEs may not be backported | Upgrade to Alpine 3.20+ at next maintenance window |

All residual findings share the same property: **they are system-level packages in the base OS that are not reachable through any OTP Messenger code path**. No web request can trigger these vulnerabilities.

---

## 6. Methodology

1. Images were built using `docker compose build`
2. Scans were executed using `aquasec/trivy:latest` with `--severity HIGH,CRITICAL`
3. Trivy vulnerability database was downloaded fresh at scan time (2026-06-22)
4. Identified fixable CVEs were remediated; images were rebuilt and rescanned to confirm
5. Raw scan output is preserved in `security_assessment/trivy_*.txt` for audit purposes

---

## 7. Container Platform SRG Alignment

| SRG Control | Requirement | Original | Final |
|---|---|---|---|
| V-205076 | Use patched base images | nginx:1.21 (EOL), python:3.9 (EOL) — 1,403 CVEs | python:3.11-slim (current), nginx:1.25-alpine + apk upgrade — 14 CVEs |
| V-205072 | Non-root user | Root (UID 0) | UID 999 (otp) |
| V-205070 | Drop capabilities | All default caps retained | cap_drop: ALL; minimal adds |
| V-205108 | Read-only filesystem | Not set | `read_only: true` |
| V-205041 | Resource limits | None | CPU and memory limits defined |

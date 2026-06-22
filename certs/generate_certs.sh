#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Certificate Generation Script — OTP Messenger
# Generates:
#   1. 4096-bit RSA server key + self-signed certificate (SHA-256)
#   2. 4096-bit DH parameters for DHE key exchange
#
# NIST SP 800-52 Rev 2 compliance:
#   - RSA key ≥ 2048 bits (we use 4096) §3.2
#   - Certificate signed with SHA-256 §3.2
#   - DH parameters ≥ 2048 bits (we use 4096) §3.2.1.1
#
# NOTE: Self-signed certificates are for development/test use only.
# Production deployments MUST use certificates issued by a NIST-approved
# CA or a DoD-issued PKI certificate.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="${SCRIPT_DIR}"

echo "[*] Generating 4096-bit RSA private key..."
openssl genrsa -out "${CERT_DIR}/server.key" 4096

# Secure the key file
chmod 600 "${CERT_DIR}/server.key"

echo "[*] Generating self-signed certificate (SHA-256, validity 365 days)..."
openssl req \
    -new \
    -x509 \
    -key "${CERT_DIR}/server.key" \
    -out "${CERT_DIR}/server.crt" \
    -days 365 \
    -config "${CERT_DIR}/openssl.cnf" \
    -extensions v3_ca

chmod 644 "${CERT_DIR}/server.crt"

echo "[*] Generating 4096-bit DH parameters (this may take several minutes)..."
openssl dhparam -out "${CERT_DIR}/dhparam.pem" 4096

chmod 644 "${CERT_DIR}/dhparam.pem"

echo ""
echo "[+] Certificate information:"
openssl x509 -in "${CERT_DIR}/server.crt" -noout -text \
    | grep -E "(Subject:|Issuer:|Not Before|Not After|Public-Key:|Signature Algorithm)"

echo ""
echo "[+] Files generated:"
ls -la "${CERT_DIR}/"*.{crt,key,pem} 2>/dev/null

echo ""
echo "[!] IMPORTANT: This is a self-signed certificate."
echo "    Replace with a CA-signed certificate before production deployment."
echo "    Distribute the CA certificate to all clients to establish trust."

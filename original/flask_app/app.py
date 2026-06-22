"""
Original OTP Application - Baseline Implementation
WARNING: This implementation is intentionally NOT hardened.
It exists as the pre-remediation baseline for security assessment comparison.
"""
import os
import base64
import logging

from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)
# SECURITY FINDING: Hardcoded secret key (APSC-DV-003280 / V-222400)
app.secret_key = 'supersecretkey123'

# SECURITY FINDING: Basic logging with no structured format; logs sensitive data
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def otp_encrypt(plaintext: str):
    data = plaintext.encode('utf-8')
    key = os.urandom(len(data))
    ciphertext = bytes(p ^ k for p, k in zip(data, key))
    ct_b64 = base64.b64encode(ciphertext).decode()
    key_b64 = base64.b64encode(key).decode()
    # SECURITY FINDING: Sensitive data (plaintext) written to log (APSC-DV-003200)
    logger.debug(f"Encrypted message: '{plaintext}' -> ciphertext: {ct_b64}")
    return ct_b64, key_b64


def otp_decrypt(ct_b64: str, key_b64: str):
    ciphertext = base64.b64decode(ct_b64)
    key = base64.b64decode(key_b64)
    # SECURITY FINDING: No length check before XOR
    plaintext = bytes(c ^ k for c, k in zip(ciphertext, key))
    decoded = plaintext.decode('utf-8')
    # SECURITY FINDING: Decrypted plaintext written to log (APSC-DV-003200)
    logger.debug(f"Decrypted message: '{decoded}'")
    return decoded


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/encrypt', methods=['POST'])
def encrypt():
    # SECURITY FINDING: No input length validation or CSRF protection
    message = request.form.get('message', '')
    ct_b64, key_b64 = otp_encrypt(message)
    return render_template('index.html',
                           ciphertext=ct_b64,
                           key=key_b64,
                           action='encrypt')


@app.route('/decrypt', methods=['POST'])
def decrypt():
    # SECURITY FINDING: No CSRF protection, no input validation
    ct_b64 = request.form.get('ciphertext', '')
    key_b64 = request.form.get('key', '')
    try:
        plaintext = otp_decrypt(ct_b64, key_b64)
        return render_template('index.html', plaintext=plaintext, action='decrypt')
    except Exception as e:
        # SECURITY FINDING: Raw exception message exposed to user (APSC-DV-000560)
        return f"Error decrypting: {str(e)}", 400


# SECURITY FINDING: debug=True enables Werkzeug debugger (RCE risk)
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

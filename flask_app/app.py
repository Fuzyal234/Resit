"""
OTP Messenger — Hardened Production Application
Compliant with:
  - Application Security and Development STIG (ASD STIG)
  - NIST SP 800-52 Rev 2 (TLS enforced at nginx layer)
  - Container Platform SRG
"""
import os
import secrets
import base64
import logging
import logging.handlers
from datetime import datetime

from flask import (Flask, render_template, request,
                   redirect, url_for, abort, make_response)
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from config import config


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(env: str = 'production') -> Flask:
    app = Flask(__name__)
    app.config.from_object(config[env])

    _configure_logging(app)
    _register_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)

    return app


# ---------------------------------------------------------------------------
# Logging — STIG APSC-DV-003000 / V-222430, APSC-DV-003010 / V-222432
# Fields: timestamp, severity, src_ip, method, path, status, event
# Sensitive data (plaintext, keys) is NEVER written to logs.
# ---------------------------------------------------------------------------

class _RequestFilter(logging.Filter):
    """Injects request context into log records when inside a request."""
    def filter(self, record):
        try:
            from flask import request as req
            record.remote_addr = req.remote_addr or '-'
            record.method = req.method or '-'
            record.path = req.path or '-'
        except RuntimeError:
            record.remote_addr = '-'
            record.method = '-'
            record.path = '-'
        return True


def _configure_logging(app: Flask) -> None:
    # Logs are written to stdout/stderr so Docker's log driver captures them.
    # In production, configure the Docker log driver (json-file, syslog, fluentd)
    # to forward to a centralised SIEM for STIG-compliant retention.
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(remote_addr)s | '
        '%(method)s %(path)s | %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_RequestFilter())

    level = getattr(logging, app.config['LOG_LEVEL'].upper(), logging.INFO)
    app.logger.setLevel(level)
    app.logger.addHandler(console_handler)
    app.logger.propagate = False


# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


def _register_extensions(app: Flask) -> None:
    csrf.init_app(app)
    limiter.init_app(app)


# ---------------------------------------------------------------------------
# Security headers — after every response
# APSC-DV-000460 (XSS), APSC-DV-000500 (clickjacking/CSRF mitigation)
# ---------------------------------------------------------------------------

def _register_blueprints(app: Flask) -> None:
    @app.after_request
    def apply_security_headers(response):
        # Prevent MIME-type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Deny embedding in iframes (clickjacking)
        response.headers['X-Frame-Options'] = 'DENY'
        # Strict CSP — only same-origin resources, no inline scripts
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        # Reflect XSS protection (legacy browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Restrict referrer leakage
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Deny dangerous browser features
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=()'
        )
        # No caching of OTP results
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        # Hide Flask/Python version
        response.headers['Server'] = 'OTP-Messenger'
        return response

    # Register route handlers
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/encrypt', 'encrypt',
                     limiter.limit("10 per minute")(encrypt),
                     methods=['GET', 'POST'])
    app.add_url_rule('/decrypt', 'decrypt',
                     limiter.limit("10 per minute")(decrypt),
                     methods=['GET', 'POST'])
    app.add_url_rule('/health', 'health', health)


# ---------------------------------------------------------------------------
# OTP core — APSC-DV-001750, APSC-DV-000160
# Key generation uses secrets.token_bytes() which calls os.urandom(),
# backed by the OS kernel CSPRNG (getrandom(2) on Linux ≥ 3.17).
# On a FIPS 140-2 enabled kernel this satisfies the CSPRNG requirement.
# ---------------------------------------------------------------------------

MAX_BYTES = 10_000


def _generate_otp_key(length: int) -> bytes:
    """Return `length` truly random bytes from the OS CSPRNG."""
    return secrets.token_bytes(length)


def otp_encrypt(plaintext: str) -> tuple[str, str]:
    """
    Encrypt plaintext with a freshly generated OTP key.
    Returns (ciphertext_b64, key_b64).
    The key is NEVER persisted — caller receives it once.
    """
    data = plaintext.encode('utf-8')
    if len(data) > MAX_BYTES:
        raise ValueError("Message exceeds maximum permitted size.")
    key = _generate_otp_key(len(data))
    ciphertext = bytes(p ^ k for p, k in zip(data, key))
    return (
        base64.b64encode(ciphertext).decode('ascii'),
        base64.b64encode(key).decode('ascii'),
    )


def otp_decrypt(ct_b64: str, key_b64: str) -> str:
    """
    Decrypt ciphertext using the supplied OTP key.
    Raises ValueError on any structural mismatch.
    """
    try:
        ciphertext = base64.b64decode(ct_b64, validate=True)
        key = base64.b64decode(key_b64, validate=True)
    except Exception:
        raise ValueError("Invalid Base64 encoding.")
    if len(ciphertext) != len(key):
        raise ValueError("Ciphertext and key lengths must be equal.")
    if len(ciphertext) > MAX_BYTES:
        raise ValueError("Ciphertext exceeds maximum permitted size.")
    plaintext_bytes = bytes(c ^ k for c, k in zip(ciphertext, key))
    try:
        return plaintext_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError("Decrypted bytes are not valid UTF-8. "
                         "Verify the key matches the ciphertext.")


# ---------------------------------------------------------------------------
# Forms (WTForms + CSRF — APSC-DV-000500 / V-222450)
# ---------------------------------------------------------------------------

class EncryptForm(FlaskForm):
    message = TextAreaField('Message', validators=[
        DataRequired(message='A message is required.'),
        Length(min=1, max=10000,
               message='Message must be between 1 and 10,000 characters.'),
    ])


class DecryptForm(FlaskForm):
    ciphertext = TextAreaField('Ciphertext (Base64)', validators=[
        DataRequired(message='Ciphertext is required.'),
        Length(max=20000, message='Ciphertext is too long.'),
    ])
    key = TextAreaField('OTP Key (Base64)', validators=[
        DataRequired(message='OTP key is required.'),
        Length(max=20000, message='Key is too long.'),
    ])


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def index():
    return render_template('index.html')


def encrypt():
    form = EncryptForm()
    result = None
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                ct_b64, key_b64 = otp_encrypt(form.message.data.strip())
                result = {'ciphertext': ct_b64, 'key': key_b64}
                # Audit log: operation outcome WITHOUT sensitive data
                # (APSC-DV-003010 / V-222432, APSC-DV-003200 / V-222406)
                app_logger = logging.getLogger('otp_messenger')
                app_logger.info(
                    'ENCRYPT | RESULT=SUCCESS | '
                    f'MSG_BYTES={len(base64.b64decode(ct_b64))}'
                )
            except ValueError as exc:
                app_logger = logging.getLogger('otp_messenger')
                app_logger.warning(f'ENCRYPT | RESULT=FAILURE | REASON={exc}')
                # Generic error to user — never expose internal detail
                # (APSC-DV-000560 / V-222480)
                form.message.errors.append('Encryption failed. Please try again.')
        else:
            logging.getLogger('otp_messenger').warning(
                'ENCRYPT | RESULT=VALIDATION_FAILURE | '
                f'ERRORS={form.errors}'
            )
    return render_template('encrypt.html', form=form, result=result)


def decrypt():
    form = DecryptForm()
    plaintext = None
    error = None
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                plaintext = otp_decrypt(
                    form.ciphertext.data.strip(),
                    form.key.data.strip(),
                )
                logging.getLogger('otp_messenger').info(
                    'DECRYPT | RESULT=SUCCESS'
                )
            except ValueError as exc:
                logging.getLogger('otp_messenger').warning(
                    f'DECRYPT | RESULT=FAILURE | REASON={exc}'
                )
                # Surfaces only safe, non-revealing error text
                error = str(exc)
        else:
            logging.getLogger('otp_messenger').warning(
                'DECRYPT | RESULT=VALIDATION_FAILURE'
            )
    return render_template('decrypt.html', form=form,
                           plaintext=plaintext, error=error)


def health():
    """Lightweight liveness probe; returns no sensitive information."""
    return {'status': 'ok'}, 200


# ---------------------------------------------------------------------------
# Error handlers — generic messages only (APSC-DV-000560 / V-222480)
# ---------------------------------------------------------------------------

def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(_e):
        return render_template('error.html', code=400,
                               message='Bad request.'), 400

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template('error.html', code=403,
                               message='Access denied.'), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template('error.html', code=404,
                               message='Resource not found.'), 404

    @app.errorhandler(429)
    def rate_limited(_e):
        logging.getLogger('otp_messenger').warning('RATE_LIMIT_EXCEEDED')
        return render_template('error.html', code=429,
                               message='Too many requests. Please slow down.'), 429

    @app.errorhandler(500)
    def internal_error(e):
        logging.getLogger('otp_messenger').error(f'INTERNAL_ERROR | {type(e).__name__}')
        return render_template('error.html', code=500,
                               message='An internal error occurred.'), 500

    @app.errorhandler(413)
    def too_large(_e):
        return render_template('error.html', code=413,
                               message='Request body too large.'), 413


# ---------------------------------------------------------------------------
# Entry point (used by Gunicorn: gunicorn "app:application")
# ---------------------------------------------------------------------------

application = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    # Never run with debug=True; use gunicorn in all environments
    application.run(host='127.0.0.1', port=5000, debug=False)

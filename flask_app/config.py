import os
import secrets


class Config:
    # --- Cryptographic session key (APSC-DV-003280 / V-222400) ---
    # Generated at startup from OS CSPRNG; never hardcoded.
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # --- Session security (APSC-DV-003360 / V-222406) ---
    SESSION_COOKIE_SECURE = True       # Only sent over HTTPS
    SESSION_COOKIE_HTTPONLY = True     # Not accessible via JavaScript
    SESSION_COOKIE_SAMESITE = 'Strict' # CSRF mitigation at cookie level
    PERMANENT_SESSION_LIFETIME = 1800  # 30-minute session timeout (seconds)

    # --- CSRF (APSC-DV-000500) ---
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1-hour CSRF token lifetime

    # --- Request limits ---
    MAX_CONTENT_LENGTH = 32 * 1024  # 32 KB max body; prevents DoS

    # --- OTP constraints ---
    OTP_MAX_MESSAGE_BYTES = 10_000   # Max plaintext size in bytes

    # --- Logging (stdout in containers; no file path needed) ---
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = False   # Keep False even in dev; debug=True is a CAT I finding
    TESTING = False


config = {
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'default': ProductionConfig,
}

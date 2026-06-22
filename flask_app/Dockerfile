# ── Stage 1: dependency build ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install only what pip needs; no build tools remain in final image
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: production image ────────────────────────────────────────────────
FROM python:3.11-slim

# Container Platform SRG: run as non-root (V-205072)
RUN groupadd -r otp && useradd -r -g otp -d /app -s /sbin/nologin otp

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=otp:otp . .

# Drop to non-root
USER otp

# Gunicorn: 4 workers, 30s timeout, production WSGI server
# No --bind 0.0.0.0 — nginx will reach us on the docker network
EXPOSE 5000

ENV FLASK_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" \
    || exit 1

CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--forwarded-allow-ips", "*", \
     "app:application"]

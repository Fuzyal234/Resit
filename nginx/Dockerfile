# Use pinned stable release for reproducibility
FROM nginx:1.25-alpine

# Install curl for healthcheck (busybox wget lacks --no-check-certificate flag)
# Upgrade all packages to pull latest security patches (libexpat, libxml2, etc.)
RUN apk upgrade --no-cache && apk add --no-cache curl

# Remove default configs
RUN rm /etc/nginx/conf.d/default.conf

# Copy hardened config
COPY nginx.conf /etc/nginx/nginx.conf

# SSL directory (certs are bind-mounted at runtime via docker-compose)
RUN mkdir -p /etc/nginx/ssl && chmod 700 /etc/nginx/ssl

# Drop nginx to non-root where possible (worker processes still use 'nginx' user)
# The master process must run as root to bind to 443/80; workers drop to 'nginx'
# This is controlled by the `user nginx;` directive in nginx.conf

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -skf https://localhost/health || exit 1

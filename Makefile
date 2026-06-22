.PHONY: certs build up down logs scan-original scan-final help

# ─────────────────────────────────────────────────────────────────────────────
COMPOSE      = docker compose
COMPOSE_ORIG = docker compose -f original/docker-compose.yml -p otp_original

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Certificate generation ────────────────────────────────────────────────────
certs: ## Generate TLS certificates and DH parameters
	@echo "[*] Generating certificates..."
	@bash certs/generate_certs.sh
	@echo "[+] Done. Certs in ./certs/"

# ── Final (hardened) implementation ──────────────────────────────────────────
build: ## Build final hardened Docker images
	$(COMPOSE) build

up: ## Start final implementation (requires certs)
	@if [ ! -f certs/server.crt ]; then \
	  echo "[!] No certificate found. Run: make certs"; exit 1; fi
	$(COMPOSE) up -d
	@echo "[+] OTP Messenger running:"
	@echo "    https://localhost (HTTPS)"
	@echo "    http://localhost  (redirects to HTTPS)"

down: ## Stop final implementation
	$(COMPOSE) down

logs: ## Tail application logs
	$(COMPOSE) logs -f

# ── Original (baseline) implementation ───────────────────────────────────────
build-original: ## Build original (baseline) Docker images
	$(COMPOSE_ORIG) build

up-original: ## Start original implementation
	$(COMPOSE_ORIG) up -d
	@echo "[+] Original OTP Messenger running: http://localhost:80"

down-original: ## Stop original implementation
	$(COMPOSE_ORIG) down

# ── Security scanning ─────────────────────────────────────────────────────────
scan-original: build-original ## Run Trivy scan on original images
	@echo "[*] Scanning original images..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
	  aquasec/trivy:latest image --severity HIGH,CRITICAL \
	  otp-original-flask:latest 2>&1 | tee security_assessment/trivy_original_flask.txt
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
	  aquasec/trivy:latest image --severity HIGH,CRITICAL \
	  otp-original-nginx:latest 2>&1 | tee security_assessment/trivy_original_nginx.txt

scan-final: build ## Run Trivy scan on final hardened images
	@echo "[*] Scanning final images..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
	  aquasec/trivy:latest image --severity HIGH,CRITICAL \
	  otp-flask:latest 2>&1 | tee security_assessment/trivy_final_flask.txt
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
	  aquasec/trivy:latest image --severity HIGH,CRITICAL \
	  otp-nginx:latest 2>&1 | tee security_assessment/trivy_final_nginx.txt

scan-all: scan-original scan-final ## Scan both implementations
	@echo "[+] Scan results written to security_assessment/"

# ── TLS verification ──────────────────────────────────────────────────────────
test-tls: ## Verify TLS cipher suite compliance (requires running final stack)
	@echo "[*] Testing TLS configuration..."
	@openssl s_client -connect localhost:443 \
	  -tls1_2 -brief 2>&1 | head -20
	@echo ""
	@echo "[*] Testing TLS 1.3..."
	@openssl s_client -connect localhost:443 \
	  -tls1_3 -brief 2>&1 | head -20
	@echo ""
	@echo "[*] Testing that TLS 1.1 is REJECTED (expected: handshake failure)..."
	@openssl s_client -connect localhost:443 \
	  -tls1_1 -brief 2>&1 | head -5 || true

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: down down-original ## Stop all containers and remove images
	$(COMPOSE) rm -f
	$(COMPOSE_ORIG) rm -f
	docker rmi otp-flask:latest otp-nginx:latest \
	           otp-original-flask:latest otp-original-nginx:latest 2>/dev/null || true

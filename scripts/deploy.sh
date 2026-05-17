#!/usr/bin/env bash
# =============================================================================
# PCC AI Portal — Deploy Script
# Usage:
#   ./scripts/deploy.sh infra        # Start PostgreSQL + Redis only
#   ./scripts/deploy.sh core         # Start infra + LiteLLM + Backend + Open-WebUI
#   ./scripts/deploy.sh monitoring   # Start monitoring stack (Prometheus + Grafana + Alertmanager)
#   ./scripts/deploy.sh all          # Start core + monitoring
#   ./scripts/deploy.sh down         # Stop all services (keep volumes)
#   ./scripts/deploy.sh reset        # Stop all + remove volumes (full reset)
#   ./scripts/deploy.sh status       # Show running containers + health
#   ./scripts/deploy.sh logs [svc]   # Tail logs (optional: service name)
#   ./scripts/deploy.sh build        # (Re)build backend image
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${PROJECT_ROOT}/infrastructure"
ENV_FILE="${INFRA_DIR}/.env"
COMPOSE="docker compose --env-file ${ENV_FILE} -f ${INFRA_DIR}/docker-compose.yml"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
header()  { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}\n"; }

# ── Preflight ────────────────────────────────────────────────────────────────
preflight() {
  if ! command -v docker &>/dev/null; then
    error "Docker not found. Install Docker Desktop or Docker Engine first."
    exit 1
  fi
  if ! docker compose version &>/dev/null; then
    error "Docker Compose v2 not found. Update Docker Desktop or install compose plugin."
    exit 1
  fi
  if [[ ! -f "${ENV_FILE}" ]]; then
    warn ".env not found — copying from .env.example"
    cp "${INFRA_DIR}/.env.example" "${ENV_FILE}"
    warn "Edit ${ENV_FILE} and set ENCRYPTION_KEY, AWS credentials, passwords before continuing."
    exit 1
  fi
  # Validate required vars
  local required=(ENCRYPTION_KEY)
  for var in "${required[@]}"; do
    local val
    val=$(grep -E "^${var}=" "${ENV_FILE}" | cut -d= -f2- | tr -d '"' || true)
    if [[ -z "${val}" || "${val}" == "changeme"* ]]; then
      error "${var} is not set or still default in ${ENV_FILE}"
      exit 1
    fi
  done
}

# ── Build ────────────────────────────────────────────────────────────────────
cmd_build() {
  header "Building backend image"
  ${COMPOSE} build --no-cache backend
  success "Backend image built."
}

# ── Infra (postgres + redis) ─────────────────────────────────────────────────
cmd_infra() {
  header "Starting infrastructure layer (PostgreSQL + Redis)"
  ${COMPOSE} up -d postgres redis
  info "Waiting for postgres to be healthy..."
  local retries=0
  until ${COMPOSE} exec -T postgres pg_isready -q 2>/dev/null; do
    retries=$((retries + 1))
    if [[ ${retries} -ge 30 ]]; then
      error "PostgreSQL did not become healthy after 30s"
      exit 1
    fi
    sleep 1
  done
  success "PostgreSQL healthy."
  info "Waiting for redis to be healthy..."
  retries=0
  local redis_pass
  redis_pass=$(grep -E '^REDIS_PASSWORD=' "${ENV_FILE}" | cut -d= -f2- | tr -d '"' || echo "changeme")
  until ${COMPOSE} exec -T redis redis-cli -a "${redis_pass}" ping 2>/dev/null | grep -q PONG; do
    retries=$((retries + 1))
    if [[ ${retries} -ge 30 ]]; then
      error "Redis did not become healthy after 30s"
      exit 1
    fi
    sleep 1
  done
  success "Redis healthy."
  echo ""
  success "Infrastructure layer up."
}

# ── Core (infra + litellm + backend + open-webui) ───────────────────────────
cmd_core() {
  cmd_infra
  header "Starting core services (LiteLLM + Backend + Open-WebUI)"
  ${COMPOSE} up -d --build backend
  ${COMPOSE} up -d litellm
  info "Waiting for LiteLLM to be healthy (may take up to 5 min on first run)..."
  local retries=0
  until ${COMPOSE} exec -T litellm python3 -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:4000/health/liveliness')" \
    2>/dev/null; do
    retries=$((retries + 1))
    if [[ ${retries} -ge 60 ]]; then
      warn "LiteLLM health check timed out — it may still be initialising. Check: docker compose logs litellm"
      break
    fi
    sleep 5
  done
  success "LiteLLM up (or still starting — check logs)."
  ${COMPOSE} up -d open-webui
  echo ""
  success "Core services up."
  echo ""
  echo -e "  ${BOLD}Open-WebUI:${NC}       http://localhost:3000"
  echo -e "  ${BOLD}LiteLLM UI:${NC}       http://localhost:4000/ui"
  echo -e "  ${BOLD}Backend API docs:${NC}  http://localhost:8001/docs"
  echo ""
}

# ── Monitoring ───────────────────────────────────────────────────────────────
cmd_monitoring() {
  header "Starting monitoring stack (Prometheus + Grafana + Alertmanager)"
  ${COMPOSE} --profile monitoring up -d \
    redis-exporter postgres-exporter alertmanager prometheus grafana
  info "Waiting for Prometheus to be ready..."
  local retries=0
  until ${COMPOSE} exec -T prometheus wget -q --spider http://localhost:9090/-/ready 2>/dev/null; do
    retries=$((retries + 1))
    if [[ ${retries} -ge 20 ]]; then
      warn "Prometheus health check timed out."
      break
    fi
    sleep 2
  done
  success "Monitoring stack up."
  echo ""
  echo -e "  ${BOLD}Grafana:${NC}          http://localhost:3001  (admin / \$GF_SECURITY_ADMIN_PASSWORD)"
  echo -e "  ${BOLD}Prometheus:${NC}       http://localhost:9090"
  echo -e "  ${BOLD}Alertmanager:${NC}     http://localhost:9093"
  echo ""
}

# ── All ──────────────────────────────────────────────────────────────────────
cmd_all() {
  cmd_core
  cmd_monitoring
}

# ── Down ─────────────────────────────────────────────────────────────────────
cmd_down() {
  header "Stopping all services (volumes preserved)"
  ${COMPOSE} --profile monitoring down
  success "All services stopped."
}

# ── Reset ────────────────────────────────────────────────────────────────────
cmd_reset() {
  header "Full reset — stopping services and removing ALL volumes"
  warn "This will delete all data in PostgreSQL, Redis, Prometheus, and Grafana."
  read -r -p "Are you sure? Type 'yes' to confirm: " confirm
  if [[ "${confirm}" != "yes" ]]; then
    info "Reset cancelled."
    exit 0
  fi
  ${COMPOSE} --profile monitoring down -v
  success "All services stopped and volumes removed."
}

# ── Status ───────────────────────────────────────────────────────────────────
cmd_status() {
  header "Service status"
  ${COMPOSE} --profile monitoring ps
  echo ""
  header "Health summary"
  local services=(pcc-postgres pcc-redis pcc-litellm pcc-backend pcc-open-webui pcc-prometheus pcc-grafana pcc-alertmanager pcc-redis-exporter pcc-postgres-exporter)
  for svc in "${services[@]}"; do
    local state
    state=$(docker inspect --format='{{.State.Health.Status}}' "${svc}" 2>/dev/null || echo "not found")
    if [[ "${state}" == "healthy" ]]; then
      echo -e "  ${GREEN}healthy${NC}    ${svc}"
    elif [[ "${state}" == "not found" ]]; then
      echo -e "  ${YELLOW}not found${NC}  ${svc}"
    else
      echo -e "  ${RED}${state}${NC}     ${svc}"
    fi
  done
  echo ""
}

# ── Logs ─────────────────────────────────────────────────────────────────────
cmd_logs() {
  local svc="${1:-}"
  if [[ -n "${svc}" ]]; then
    ${COMPOSE} --profile monitoring logs -f --tail=100 "${svc}"
  else
    ${COMPOSE} --profile monitoring logs -f --tail=50
  fi
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  local cmd="${1:-help}"

  if [[ "${cmd}" != "help" && "${cmd}" != "--help" && "${cmd}" != "-h" ]]; then
    preflight
  fi

  case "${cmd}" in
    build)      cmd_build ;;
    infra)      cmd_infra ;;
    core)       cmd_core ;;
    monitoring) cmd_monitoring ;;
    all)        cmd_all ;;
    down)       cmd_down ;;
    reset)      cmd_reset ;;
    status)     cmd_status ;;
    logs)       cmd_logs "${2:-}" ;;
    help|--help|-h)
      echo ""
      echo -e "${BOLD}PCC AI Portal — Deploy Script${NC}"
      echo ""
      echo "Usage: ./scripts/deploy.sh <command> [args]"
      echo ""
      echo "Commands:"
      echo "  build       (Re)build backend Docker image"
      echo "  infra       Start PostgreSQL + Redis"
      echo "  core        Start full app stack (infra + LiteLLM + Backend + Open-WebUI)"
      echo "  monitoring  Start monitoring stack (Prometheus + Grafana + Alertmanager)"
      echo "  all         Start core + monitoring"
      echo "  down        Stop all services (volumes preserved)"
      echo "  reset       Stop all + remove volumes (full data reset)"
      echo "  status      Show container health summary"
      echo "  logs [svc]  Tail logs (all services, or specific service name)"
      echo ""
      echo "Typical first-run:"
      echo "  cd $(dirname "${BASH_SOURCE[0]}")/.."
      echo "  cp infrastructure/.env.example infrastructure/.env"
      echo "  # edit infrastructure/.env"
      echo "  ./scripts/deploy.sh all"
      echo ""
      ;;
    *)
      error "Unknown command: ${cmd}"
      echo "Run './scripts/deploy.sh help' for usage."
      exit 1
      ;;
  esac
}

main "$@"

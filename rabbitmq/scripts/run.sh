#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="lab-amqp-rabbitmq"
CONTAINER_NAME="lab-amqp-rabbitmq"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p "$PROJECT_NAME")

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: docker compose plugin not available" >&2; exit 1; }
[[ -f docker-compose.yml ]] || { echo "ERROR: docker-compose.yml not found in $PROJECT_DIR" >&2; exit 1; }
[[ -f config/rabbitmq.conf ]] || { echo "ERROR: config/rabbitmq.conf not found" >&2; exit 1; }

if [[ ! -f .env ]]; then
  [[ -f .env.example ]] || { echo "ERROR: .env.example not found" >&2; exit 1; }
  umask 077
  pass="$(openssl rand -hex 16)"
  sed "s|^RABBITMQ_DEFAULT_PASS=.*|RABBITMQ_DEFAULT_PASS=${pass}|" .env.example > .env
  chmod 600 .env
  echo "Created .env with a random password (mode 600)."
fi
chmod 600 .env 2>/dev/null || true

set -a
. "$PROJECT_DIR/.env"
set +a
MQ_USER="${RABBITMQ_DEFAULT_USER:-lab_user}"
MQ_VHOST="${RABBITMQ_DEFAULT_VHOST:-/lab}"

echo "Starting $PROJECT_NAME ..."
"${COMPOSE[@]}" up -d

echo "Waiting for RabbitMQ healthcheck ..."
healthy=0
status=""
for _ in $(seq 1 60); do
  status="$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  if [[ "$status" == "healthy" ]]; then healthy=1; break; fi
  if [[ "$status" == "unhealthy" ]]; then break; fi
  sleep 2
done

if [[ "$healthy" -ne 1 ]]; then
  echo "ERROR: RabbitMQ did not become healthy (last status: ${status:-unknown})" >&2
  "${COMPOSE[@]}" logs --tail=50 >&2 || true
  exit 1
fi

echo "Applying lab_user configuration (idempotent) ..."
"${COMPOSE[@]}" exec -T rabbitmq rabbitmqctl set_user_tags "$MQ_USER" management
if ! "${COMPOSE[@]}" exec -T rabbitmq rabbitmqctl list_vhosts name | grep -qx "$MQ_VHOST"; then
  "${COMPOSE[@]}" exec -T rabbitmq rabbitmqctl add_vhost "$MQ_VHOST"
fi
"${COMPOSE[@]}" exec -T rabbitmq rabbitmqctl set_permissions -p "$MQ_VHOST" "$MQ_USER" ".*" ".*" ".*"

"${COMPOSE[@]}" ps
echo "RabbitMQ is up."

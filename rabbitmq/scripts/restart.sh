#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p lab-amqp-rabbitmq)
echo "Restarting lab-amqp-rabbitmq ..."
"${COMPOSE[@]}" up -d --force-recreate

for _ in $(seq 1 60); do
  status="$(docker inspect --format '{{.State.Health.Status}}' lab-amqp-rabbitmq 2>/dev/null || true)"
  [[ "$status" == "healthy" ]] && break
  [[ "$status" == "unhealthy" ]] && break
  sleep 2
done
if [[ "$status" != "healthy" ]]; then
  echo "ERROR: RabbitMQ did not become healthy after restart (status: ${status:-unknown})" >&2
  "${COMPOSE[@]}" logs --tail=50 >&2 || true
  exit 1
fi
"${COMPOSE[@]}" ps

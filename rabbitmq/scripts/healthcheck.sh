#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p lab-amqp-rabbitmq)
PASS=""
if [[ -f .env ]]; then
  set -a
  . "$PROJECT_DIR/.env"
  set +a
  PASS="${RABBITMQ_DEFAULT_PASS:-}"
  MQ_USER="${RABBITMQ_DEFAULT_USER:-lab_user}"
  MQ_VHOST="${RABBITMQ_DEFAULT_VHOST:-/lab}"
fi
MQ_USER="${MQ_USER:-lab_user}"
MQ_VHOST="${MQ_VHOST:-/lab}"

fail=0
ok()  { printf '  [OK] %s\n' "$1"; }
bad() { printf '  [FAIL] %s\n' "$1"; fail=$((fail + 1)); }

echo "RabbitMQ:"

state="$(docker inspect --format '{{.State.Running}}' lab-amqp-rabbitmq 2>/dev/null || true)"
if [[ "$state" == "true" ]]; then ok "Container running"; else bad "Container running"; fi

if "${COMPOSE[@]}" exec -T rabbitmq rabbitmq-diagnostics -q ping >/dev/null 2>&1; then
  ok "Broker diagnostics"
else
  bad "Broker diagnostics"
fi

if nc -z -w 3 127.0.0.1 5672 >/dev/null 2>&1; then
  ok "AMQP port"
else
  bad "AMQP port"
fi

if [[ -n "$PASS" ]] && curl -fsS -u "$MQ_USER:$PASS" http://127.0.0.1:15672/api/whoami 2>/dev/null | grep -q "\"name\":\"$MQ_USER\""; then
  ok "Authentication"
else
  bad "Authentication"
fi

if [[ -n "$PASS" ]] && curl -fsS -u "$MQ_USER:$PASS" http://127.0.0.1:15672/api/vhosts 2>/dev/null | grep -q "\"name\":\"$MQ_VHOST\""; then
  ok "Virtual host"
else
  bad "Virtual host"
fi

QUEUE="lab-healthcheck-$$"
cleanup() {
  "${COMPOSE[@]}" exec -T rabbitmq rabbitmqadmin -H localhost -P 15672 -u "$MQ_USER" -p "$PASS" -V "$MQ_VHOST" --non-interactive delete queue --name "$QUEUE" --idempotently </dev/null >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [[ -n "$PASS" ]] \
  && "${COMPOSE[@]}" exec -T rabbitmq rabbitmqadmin -H localhost -P 15672 -u "$MQ_USER" -p "$PASS" -V "$MQ_VHOST" --non-interactive declare queue --name "$QUEUE" --durable true --auto-delete false </dev/null >/dev/null 2>&1 \
  && "${COMPOSE[@]}" exec -T rabbitmq rabbitmqadmin -H localhost -P 15672 -u "$MQ_USER" -p "$PASS" -V "$MQ_VHOST" --non-interactive publish message --exchange amq.default --routing-key "$QUEUE" --payload "lab-amqp-healthcheck" </dev/null >/dev/null 2>&1 \
  && "${COMPOSE[@]}" exec -T rabbitmq rabbitmqadmin -H localhost -P 15672 -u "$MQ_USER" -p "$PASS" -V "$MQ_VHOST" --non-interactive get messages --queue "$QUEUE" --ack-mode ack_requeue_false </dev/null 2>/dev/null | grep -q "lab-amqp-healthcheck"; then
  ok "Publish / Consume"
else
  bad "Publish / Consume"
fi

trap - EXIT
cleanup

echo
if [[ "$fail" -eq 0 ]]; then
  exit 0
else
  exit 1
fi

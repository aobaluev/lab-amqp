#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p lab-amqp-rabbitmq)
"${COMPOSE[@]}" ps -a
echo
echo "Compose project: lab-amqp-rabbitmq"
echo "AMQP:            0.0.0.0:5672"
echo "Management UI:   127.0.0.1:15672 (loopback only, use SSH tunnel)"
echo "Vhost:           /lab"
echo "User:            lab_user"
echo
printf 'Health status:   '
docker inspect --format '{{.State.Health.Status}}' lab-amqp-rabbitmq 2>/dev/null || echo "unknown (container missing)"

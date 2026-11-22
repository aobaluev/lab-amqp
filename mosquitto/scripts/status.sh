#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p lab-amqp-mosquitto)
"${COMPOSE[@]}" ps -a
echo
echo "Compose project: lab-amqp-mosquitto"
echo "MQTT:            0.0.0.0:1883"
echo "User:            lab_user"
echo "Anonymous:       denied"
echo
printf 'Health status:   '
docker inspect --format '{{.State.Health.Status}}' lab-amqp-mosquitto 2>/dev/null || echo "unknown (container missing)"

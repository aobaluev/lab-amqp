#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p lab-amqp-mosquitto)
echo "Removing lab-amqp-mosquitto containers and networks (data volume is preserved) ..."
"${COMPOSE[@]}" down --remove-orphans
echo "Remaining Mosquitto volumes:"
docker volume ls --filter "name=lab-amqp-mosquitto" || true

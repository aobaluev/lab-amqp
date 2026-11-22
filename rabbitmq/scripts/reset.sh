#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p lab-amqp-rabbitmq)

if [[ "${1:-}" != "--yes" ]]; then
  if [[ ! -t 0 ]]; then
    echo "ERROR: refusing non-interactive reset without --yes" >&2
    exit 1
  fi
  echo "WARNING: this permanently deletes the RabbitMQ data volume lab-amqp-rabbitmq-data."
  echo "         Queues, messages, users and vhosts created at runtime will be lost."
  read -r -p "Type RESET to continue: " answer
  if [[ "$answer" != "RESET" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

echo "Resetting lab-amqp-rabbitmq ..."
"${COMPOSE[@]}" down -v --remove-orphans
echo "Reset complete. The next run.sh will create a fresh broker and .env if needed."

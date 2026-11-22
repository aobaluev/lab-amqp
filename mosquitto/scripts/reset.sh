#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p lab-amqp-mosquitto)

if [[ "${1:-}" != "--yes" ]]; then
  if [[ ! -t 0 ]]; then
    echo "ERROR: refusing non-interactive reset without --yes" >&2
    exit 1
  fi
  echo "WARNING: this permanently deletes the Mosquitto data volume lab-amqp-mosquitto-data."
  echo "         Queued messages, persistent sessions and retained messages will be lost."
  read -r -p "Type RESET to continue: " answer
  if [[ "$answer" != "RESET" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

echo "Resetting lab-amqp-mosquitto ..."
"${COMPOSE[@]}" down -v --remove-orphans
echo "Reset complete. The next run.sh will recreate the broker and credentials."

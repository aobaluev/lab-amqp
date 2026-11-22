#!/usr/bin/env bash
# run-amqp-consumer.sh - Run AMQP consumer
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  echo "ERROR: .env not found. Copy .env.example to .env and fill in values." >&2
  exit 1
fi

set -a
. "$PROJECT_DIR/.env"
set +a

cd "$PROJECT_DIR"
.venv/bin/python -m lab_messaging.applications.amqp_consumer "$@"
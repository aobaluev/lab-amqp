#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

fail=0
echo "== RabbitMQ =="
if ! "$ROOT_DIR/rabbitmq/scripts/run.sh"; then
  echo "ERROR: RabbitMQ failed to start" >&2
  fail=1
fi

echo
echo "== Mosquitto =="
if ! "$ROOT_DIR/mosquitto/scripts/run.sh"; then
  echo "ERROR: Mosquitto failed to start" >&2
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  echo "ERROR: one or more brokers failed to start" >&2
  exit 1
fi
echo "All brokers are up."

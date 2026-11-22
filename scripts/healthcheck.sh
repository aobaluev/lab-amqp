#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

fail=0
echo "================================="
echo "lab-amqp infrastructure healthcheck"
echo "================================="
echo
if ! "$ROOT_DIR/rabbitmq/scripts/healthcheck.sh"; then
  fail=1
fi
echo
if ! "$ROOT_DIR/mosquitto/scripts/healthcheck.sh"; then
  fail=1
fi
echo
echo "---------------------------------"
if [[ "$fail" -eq 0 ]]; then
  echo "Result: ALL CHECKS PASSED"
  exit 0
else
  echo "Result: FAILURES DETECTED"
  exit 1
fi

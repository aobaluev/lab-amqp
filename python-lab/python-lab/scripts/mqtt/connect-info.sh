#!/usr/bin/env bash
# connect-info.sh - Show MQTT connection parameters (no password)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"

# Read from mosquitto .env if available
MOSQUITTO_ENV="$PROJECT_DIR/mosquitto/.env"
if [[ -f "$MOSQUITTO_ENV" ]]; then
  # shellcheck disable=SC1090
  set -a
  . "$MOSQUITTO_ENV"
  set +a
fi

HOST="${MQTT_HOST:-127.0.0.1}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-lab_user}"

echo "MQTT connection info (from mosquitto .env):"
echo "  Host:    $HOST"
echo "  Port:    $PORT"
echo "  User:    $USER"
echo "  Password: (not shown - see mosquitto/.env)"
echo

# Check broker availability
if command -v nc >/dev/null 2>&1; then
  if nc -z "$HOST" "$PORT" 2>/dev/null; then
    echo "Broker is reachable on $HOST:$PORT"
  else
    echo "WARNING: Broker not reachable on $HOST:$PORT"
  fi
elif command -v bash >/dev/null 2>&1; then
  if bash -c "timeout 2 bash -c '</dev/tcp/$HOST/$PORT'" 2>/dev/null; then
    echo "Broker is reachable on $HOST:$PORT"
  else
    echo "WARNING: Broker not reachable on $HOST:$PORT"
  fi
fi
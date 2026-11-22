#!/usr/bin/env bash
# sub.sh - Subscribe to MQTT topic(s)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"

MOSQUITTO_ENV="$PROJECT_DIR/mosquitto/.env"
if [[ -f "$MOSQUITTO_ENV" ]]; then
  set -a
  . "$MOSQUITTO_ENV"
  set +a
fi

HOST="${MQTT_HOST:-127.0.0.1}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-lab_user}"
PASSWORD="${MQTT_PASSWORD:-}"

TOPIC="${1:-lab/#}"
QOS="${2:-1}"

if [[ -z "$PASSWORD" ]]; then
  echo "ERROR: MQTT_PASSWORD not set in $MOSQUITTO_ENV" >&2
  exit 1
fi

echo "Subscribing to $TOPIC (QoS $QOS) on $HOST:$PORT ..."
echo "Press Ctrl+C to stop."
mosquitto_sub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASSWORD" -t "$TOPIC" -q "$QOS" -v
#!/usr/bin/env bash
# pub.sh - Publish a message to MQTT
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

TOPIC="${1:-}"
MESSAGE="${2:-}"
QOS="${3:-1}"

if [[ -z "$TOPIC" ]]; then
  echo "Usage: $0 <topic> [message] [qos]"
  exit 1
fi

if [[ -z "$PASSWORD" ]]; then
  echo "ERROR: MQTT_PASSWORD not set in $MOSQUITTO_ENV" >&2
  exit 1
fi

mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASSWORD" -t "$TOPIC" -m "$MESSAGE" -q "$QOS"
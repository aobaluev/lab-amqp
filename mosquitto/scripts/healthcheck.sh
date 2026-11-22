#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p lab-amqp-mosquitto)
MQTT_USER="lab_user"
MQTT_PASSWORD=""
if [[ -f .env ]]; then
  set -a
  . "$PROJECT_DIR/.env"
  set +a
  MQTT_USER="${MQTT_USER:-lab_user}"
  MQTT_PASSWORD="${MQTT_PASSWORD:-}"
fi

fail=0
ok()  { printf '  [OK] %s\n' "$1"; }
bad() { printf '  [FAIL] %s\n' "$1"; fail=$((fail + 1)); }

echo "Mosquitto:"

state="$(docker inspect --format '{{.State.Running}}' lab-amqp-mosquitto 2>/dev/null || true)"
if [[ "$state" == "true" ]]; then ok "Container running"; else bad "Container running"; fi

if nc -z -w 3 127.0.0.1 1883 >/dev/null 2>&1; then
  ok "MQTT port"
else
  bad "MQTT port"
fi

AUTH_TOPIC="lab/healthcheck/auth-$$"
if [[ -n "$MQTT_PASSWORD" ]] && timeout 5 mosquitto_pub -h 127.0.0.1 -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -q 1 -t "$AUTH_TOPIC" -m "auth-ok" >/dev/null 2>&1; then
  ok "Authentication"
else
  bad "Authentication"
fi

TOPIC="lab/healthcheck/$$"
OUT="$(mktemp)"
SUB_PID=""
if [[ -n "$MQTT_PASSWORD" ]]; then
  mosquitto_sub -h 127.0.0.1 -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -q 1 -t "$TOPIC" -C 1 -W 6 >"$OUT" 2>/dev/null &
  SUB_PID=$!
  sleep 1
  PUB_RC=0
  timeout 5 mosquitto_pub -h 127.0.0.1 -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -q 1 -t "$TOPIC" -m "lab-amqp-healthcheck" >/dev/null 2>&1 || PUB_RC=$?
  if [[ -n "$SUB_PID" ]]; then wait "$SUB_PID" 2>/dev/null || true; fi
  if [[ "$PUB_RC" -eq 0 ]] && grep -q "lab-amqp-healthcheck" "$OUT"; then
    ok "Publish / Subscribe"
  else
    bad "Publish / Subscribe"
  fi
else
  bad "Publish / Subscribe"
fi
rm -f "$OUT"

if timeout 5 mosquitto_pub -h 127.0.0.1 -p 1883 -q 1 -t "lab/healthcheck/anon-$$" -m "should-fail" >/dev/null 2>&1; then
  bad "Anonymous access denied"
else
  ok "Anonymous access denied"
fi

echo
if [[ "$fail" -eq 0 ]]; then
  exit 0
else
  exit 1
fi

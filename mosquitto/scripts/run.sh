#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "ERROR: ${BASH_SOURCE[0]}:$LINENO: command failed" >&2' ERR

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="lab-amqp-mosquitto"
CONTAINER_NAME="lab-amqp-mosquitto"
IMAGE="eclipse-mosquitto:2.1.4-alpine"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -p "$PROJECT_NAME")

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: docker compose plugin not available" >&2; exit 1; }
[[ -f docker-compose.yml ]] || { echo "ERROR: docker-compose.yml not found in $PROJECT_DIR" >&2; exit 1; }
[[ -f config/mosquitto.conf ]] || { echo "ERROR: config/mosquitto.conf not found" >&2; exit 1; }

if [[ ! -f .env ]]; then
  [[ -f .env.example ]] || { echo "ERROR: .env.example not found" >&2; exit 1; }
  umask 077
  pass="$(openssl rand -hex 16)"
  sed "s|^MQTT_PASSWORD=.*|MQTT_PASSWORD=${pass}|" .env.example > .env
  chmod 600 .env
  echo "Created .env with a random password (mode 600)."
fi
chmod 600 .env 2>/dev/null || true

set -a
. "$PROJECT_DIR/.env"
set +a
MQTT_USER="${MQTT_USER:-lab_user}"
if [[ -z "${MQTT_PASSWORD:-}" || "$MQTT_PASSWORD" == CHANGE_ME* ]]; then
  echo "ERROR: MQTT_PASSWORD is not set in .env" >&2
  exit 1
fi

mkdir -p config
echo "Generating config/passwd with mosquitto_passwd ..."
umask 077
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$PROJECT_DIR/config:/mosquitto/config" \
  --entrypoint mosquitto_passwd \
  "$IMAGE" -c -b /mosquitto/config/passwd "$MQTT_USER" "$MQTT_PASSWORD"
chmod 644 config/passwd

echo "Starting $PROJECT_NAME ..."
"${COMPOSE[@]}" up -d

echo "Waiting for Mosquitto healthcheck ..."
healthy=0
status=""
for _ in $(seq 1 30); do
  status="$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  if [[ "$status" == "healthy" ]]; then healthy=1; break; fi
  if [[ "$status" == "unhealthy" ]]; then break; fi
  sleep 2
done

if [[ "$healthy" -ne 1 ]]; then
  echo "ERROR: Mosquitto did not become healthy (last status: ${status:-unknown})" >&2
  "${COMPOSE[@]}" logs --tail=50 >&2 || true
  exit 1
fi

"${COMPOSE[@]}" ps
echo "Mosquitto is up."

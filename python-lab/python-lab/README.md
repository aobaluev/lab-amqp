# Python Messaging Lab: MQTT, AMQP, JSON Contracts

A self-contained Python laboratory for learning and testing messaging patterns
with Mosquitto (MQTT), RabbitMQ (AMQP), JSON contract versioning, validation,
and message bridging between brokers.

## Architecture

```text
Python MQTT Publisher
           |
           v
       Mosquitto (MQTT 1883)
           |
           v
Python MQTT → AMQP Bridge
           |
           v
      RabbitMQ (AMQP 5672)
           |
   +-------+-------+
   |               |
   v               v
lab.heartbeat   lab.commands
   |               |
   v               v
Python Consumer  Command Dispatcher
 Log / Stats      Handlers (demo only)
```

All components are small, standalone Python applications. No C++, no async
frameworks, no Docker for Python apps — they run directly on the host.

## Prerequisites

The lab requires the infrastructure from the previous stage:

- **Mosquitto** on `127.0.0.1:1883` (user `lab_user`, password from `.env`)
- **RabbitMQ** on `127.0.0.1:5672`, vhost `/lab` (user `lab_user`)

Start them with:

```bash
/home/user/lab-amqp/scripts/run-all.sh
```

## Installation

Python 3.11+ is required. The preferred tool is `uv`.

```bash
cd /home/user/lab-amqp/python-lab

# Create .env from example
cp .env.example .env
# Edit .env with real values (do not commit it)

# Create virtual environment and install dependencies
uv venv --python 3.11
uv sync

# Activate
source .venv/bin/activate
```

If `uv` is not available, use `venv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pika paho-mqtt pydantic pytest
```

## Configuration

All connection settings come from `.env` (created from `.env.example`).
Never commit `.env`. Secrets are never logged.

Key variables:

| Variable | Description | Example |
|---|---|---|
| `RABBITMQ_HOST` | RabbitMQ host | `127.0.0.1` |
| `RABBITMQ_PORT` | AMQP port | `5672` |
| `RABBITMQ_VHOST` | RabbitMQ vhost | `/lab` |
| `RABBITMQ_USER` | RabbitMQ user | `lab_user` |
| `RABBITMQ_PASSWORD` | RabbitMQ password | (from `.env`) |
| `MQTT_HOST` | Mosquitto host | `127.0.0.1` |
| `MQTT_PORT` | MQTT port | `1883` |
| `MQTT_USER` | MQTT user | `lab_user` |
| `MQTT_PASSWORD` | MQTT password | (from `.env`) |
| `LOG_LEVEL` | Logging level | `INFO` |
| `VALIDATION_MODE` | `permissive` or `strict` | `permissive` |

## Running the Applications

### MQTT Publisher

```bash
./scripts/run-mqtt-publisher.sh --topic lab/test --message "hello"
./scripts/run-mqtt-publisher.sh --heartbeat
./scripts/run-mqtt-publisher.sh --command status
```

### MQTT Subscriber

```bash
./scripts/run-mqtt-subscriber.sh --topic "lab/#"
```

### AMQP Publisher

```bash
./scripts/run-amqp-publisher.sh --routing-key heartbeat --heartbeat
./scripts/run-amqp-publisher.sh --routing-key command --command get_metrics
```

### AMQP Consumer

```bash
./scripts/run-amqp-consumer.sh --queue lab.heartbeat
./scripts/run-amqp-consumer.sh --queue lab.commands
```

### MQTT → AMQP Bridge

```bash
./scripts/run-bridge.sh
```

### Interactive Command Sender

```bash
./scripts/run-command-sender.sh
```

Menu options:
1. Send heartbeat — creates and publishes a heartbeat v1 JSON message
2. Send sample JSON — publishes a sample heartbeat JSON
3. Send custom text — enters arbitrary plain text
4. Command aliases — interactive submenu for command aliases (1–5)
5. Exit

## Full Chain Scenario

Terminal 1 — AMQP consumer:
```bash
./scripts/run-amqp-consumer.sh --queue lab.heartbeat
```

Terminal 2 — Bridge:
```bash
./scripts/run-bridge.sh
```

Terminal 3 — MQTT publisher:
```bash
./scripts/run-mqtt-publisher.sh --heartbeat
```

The heartbeat message flows: MQTT Publisher → Mosquitto → Bridge → RabbitMQ → Consumer.

## MQTT CLI Utilities

For quick checks without Python:

```bash
./scripts/mqtt/connect-info.sh
./scripts/mqtt/pub.sh lab/test "hello world"
./scripts/mqtt/sub.sh lab/test
```

## JSON Contracts

See `docs/message-contracts.md` for full contract specifications.

### Contract versions

- `heartbeat` v1 — `type: "heartbeat"`, `version: 1`
- `command` v1 — `type: "command"`, `version: 1`

### Validation modes

| Mode | Description | Extra fields | Type enforcement |
|---|---|---|---|
| `permissive` | Required fields + types only | Allowed | Basic |
| `strict` | All fields, no extras, value constraints | Forbidden | Full (Pydantic) |

Switch via `VALIDATION_MODE` environment variable. No code changes needed.

## Running Tests

```bash
# Unit tests (no brokers needed)
uv run pytest tests/unit/

# Integration tests (requires running brokers)
uv run pytest tests/integration/
```

## Manual Scenarios

See `docs/` for detailed manual test scenarios (1–6) covering MQTT direct,
AMQP direct, full chain, commands, and latency measurement.

## Known Limitations

- No exactly-once delivery guarantee between two independent brokers.
- Bridge message loss is possible if RabbitMQ is down during publish.
- Latency measurement depends on clock synchronization between publishers and consumers.
- All command handlers are simulated only — no real system actions.

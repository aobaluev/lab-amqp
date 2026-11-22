# Progress

## Stage A — Infrastructure (complete)
- [x] Fixed mosquitto `run.sh` passwd file `-c` issue
- [x] Mosquitto starts repeatedly without error (tested: first start, repeat start, stop/start)
- [x] RabbitMQ running and healthy (existing config unchanged)
- [x] MQTT pub/sub verified with mosquitto_clients
- [x] AMQP connectivity verified

## Stage B — Python Project Setup (complete)
- [x] Project structure created under `python-lab/`
- [x] `pyproject.toml` with dependencies (pika>=1.0.0,<2.0.0, paho-mqtt>=2.0.0,<3.0.0, pydantic>=2.0.0,<3.0.0)
- [x] `.env.example` and `.gitignore`
- [x] `uv` installed on stand, `uv.lock` generated
- [x] Python 3.11 virtual environment (`.venv`)
- [x] `.env` with real credentials (not committed)

## Stage C — MQTT Client (complete)
- [x] MQTT publisher (JSON, text, heartbeat, command)
- [x] MQTT subscriber (topic/wildcard, QoS, latency display)
- [x] Logging and graceful shutdown (SIGINT/SIGTERM)

## Stage D — JSON Contracts (complete)
- [x] heartbeat v1 (permissive + strict with Pydantic)
- [x] command v1 (permissive + strict with Pydantic)
- [x] Validation mode selection via VALIDATION_MODE env var
- [x] Contract comparison tests (permissive vs strict)

## Stage E — AMQP Client (complete)
- [x] Publisher with Publisher Confirms (pika 1.x compatible)
- [x] Consumer with manual ACK
- [x] Direct exchange `lab.events`, durable queues, persistent messages
- [x] Routing keys: heartbeat, command, test

## Stage F — Bridge (complete)
- [x] MQTT → AMQP forwarding
- [x] Topic-to-routing-key mapping (lab/heartbeat→heartbeat, lab/commands→command, lab/test→test)
- [x] Contract-based validation in bridge
- [x] Non-JSON passthrough
- [x] MQTT topic preserved in AMQP headers

## Stage G — Commands (complete)
- [x] Command dispatcher with explicit handler table
- [x] 5 handlers: status, restart_service, reload_config, get_metrics, ping
- [x] All handlers are simulated only (no real system actions)
- [x] Interactive command sender with menu

## Stage H — Testing (complete)
- [x] 24 unit tests (no brokers required)
- [x] 5 integration tests (real brokers)
- [x] All 29 tests pass

## Stage I — Documentation (complete)
- [x] README.md with setup and usage instructions
- [x] docs/architecture.md
- [x] docs/message-contracts.md
- [x] docs/concepts.md
- [x] docs/decisions.md
- [x] docs/progress.md

## Manual Scenarios Verified
- [x] MQTT CLI pub/sub with UTF-8
- [x] Python MQTT publisher/subscriber
- [x] Mosquitto repeatable start
- [x] Full chain: MQTT → Bridge → AMQP → Consumer

# C++ Handoff Document

## 1. Lab Purpose

The `lab-amqp` project is a hands-on messaging laboratory for learning and testing:
- MQTT (Mosquitto broker)
- AMQP 0-9-1 (RabbitMQ broker)
- JSON contract versioning
- Permissive vs strict message validation
- Message bridging between two independent brokers
- Command routing via aliases
- Logging and latency measurement
- Automated and manual testing

**This document is a handoff for the next C++ phase.** You must implement a C++ client that speaks the same external protocol as the existing Python applications, without modifying those applications or the brokers.

---

## 2. What Is Already Deployed

| Component | Technology | Endpoint | Status |
|---|---|---|---|
| RabbitMQ (AMQP 0-9-1) | `rabbitmq:4.3.8-management` Docker image | `127.0.0.1:5672`, vhost `/lab` | Running |
| RabbitMQ Management UI | Same container | `127.0.0.1:15672` (via SSH tunnel) | Running |
| Mosquitto (MQTT 5.0-compatible) | `eclipse-mosquitto:2.1.4-alpine` Docker image | `127.0.0.1:1883` | Running |

Both brokers are managed by Docker Compose project names:
- `lab-amqp-rabbitmq`
- `lab-amqp-mosquitto`

Credentials are stored in `.env` files (not committed). The Python `.env.example` shows the required variable names.

---

## 3. Where the Project Lives

```
/home/user/lab-amqp/
├── rabbitmq/           # RabbitMQ Docker Compose, config, scripts
├── mosquitto/          # Mosquitto Docker Compose, config, scripts
├── scripts/            # run-all.sh, stop-all.sh, status-all.sh, healthcheck.sh
└── python-lab/         # Python reference implementation
    ├── src/lab_messaging/   # Python source code (reference only)
    ├── tests/               # Unit + integration tests
    ├── docs/                # Existing docs + this handoff package
    ├── pyproject.toml       # Python deps: pika, paho-mqtt, pydantic, pytest
    ├── uv.lock              # Lock file for reproducible installs
    ├── .env.example         # Connection settings template
    ├── .python-version      # Python 3.11
    └── scripts/             # Runner scripts for each Python application
```

---

## 4. Protocols Used

| Layer | Protocol | Version | Broker | Port |
|---|---|---|---|---|
| MQTT | MQTT | 5.0-compatible (mosquitto 2.x) | Mosquitto | 1883 |
| AMQP | AMQP 0-9-1 | AMQP 0-9-1 | RabbitMQ | 5672 |
| Message format | JSON | UTF-8 | N/A | N/A |

---

## 5. Documents in This Package

| Document | Purpose |
|---|---|
| `cpp-handoff.md` | This file — quick start for the C++ agent |
| `protocol-spec.md` | External protocol specification (brokers, topics, queues, contracts, compatibility) |
| `delivery-semantics.md` | Delivery guarantees, ACK semantics, bridge reliability |
| `command-protocol.md` | Command message structure, aliases, handler contract |
| `test-vectors.md` | Reference messages and integration test scenarios |
| `decisions-and-issues.md` | Architectural decisions, known issues, limitations |

---

## 6. Python Reference Applications

These Python applications implement the external protocol and serve as a compatibility target:

| Application | Role | Entry Point |
|---|---|---|
| MQTT Publisher | Publishes to Mosquitto topics | `python-lab/scripts/run-mqtt-publisher.sh` |
| MQTT Subscriber | Subscribes to Mosquitto topics | `python-lab/scripts/run-mqtt-subscriber.sh` |
| AMQP Publisher | Publishes to RabbitMQ exchange | `python-lab/scripts/run-amqp-publisher.sh` |
| AMQP Consumer | Consumes from RabbitMQ queues | `python-lab/scripts/run-amqp-consumer.sh` |
| MQTT → AMQP Bridge | Relays MQTT topics to RabbitMQ routing keys | `python-lab/scripts/run-bridge.sh` |
| Command Sender | Interactive menu / CLI sender | `python-lab/scripts/run-command-sender.sh` |

---

## 7. How to Run the Python Reference

```bash
cd /home/user/lab-amqp/python-lab

# Source .env (create from .env.example first)
set -a; . ./.env; set +a

# Activate virtualenv
source .venv/bin/activate

# Run any application
python -m lab_messaging.applications.mqtt_publisher --heartbeat
python -m lab_messaging.applications.amqp_consumer --queue lab.heartbeat
python -m lab_messaging.bridge.mqtt_to_amqp
```

Full chain test (3 terminals):

1. Terminal 1: `./scripts/run-amqp-consumer.sh --queue lab.heartbeat`
2. Terminal 2: `./scripts/run-bridge.sh`
3. Terminal 3: `./scripts/run-mqtt-publisher.sh --heartbeat`

---

## 8. Compatibility Requirements for C++

The C++ client must:

| Requirement | Detail |
|---|---|
| AMQP 0-9-1 compatible | Must work with RabbitMQ 4.3.8 |
| MQTT compatible | Must work with Mosquitto 2.1.4 |
| JSON UTF-8 | All messages encoded as UTF-8 JSON |
| Same queues/exchange | Use `lab.events` exchange, `lab.heartbeat`, `lab.commands`, `lab.test` queues |
| Same routing keys | `heartbeat`, `command`, `test` |
| Same MQTT topics | `lab/heartbeat`, `lab/commands`, `lab/test` |
| Same JSON contracts | See `protocol-spec.md` section 3 |
| Manual ACK support | Consumer should support manual acknowledgment |
| Graceful shutdown | Handle SIGINT/SIGTERM cleanly |
| No Python dependency | Must not link against Python or import any Python library |

---

## 9. Running Integration Checks

```bash
cd /home/user/lab-amqp/python-lab

# Unit tests (no brokers needed)
source .venv/bin/activate
pytest tests/unit/

# Integration tests (requires running brokers)
pytest tests/integration/
```

Expected: 29 tests pass (24 unit + 5 integration).

---

## 10. Open Questions / TODO

- No C++ AMQP/MQTT library has been selected yet — this must be decided on the next stage.
- No CMake configuration exists yet.
- The C++ standard has not been fixed yet.
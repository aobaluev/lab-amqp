# C++ Handoff Documentation

This directory contains the specification and reference materials needed to
implement a C++ client for the `lab-amqp` messaging laboratory.

The Python stage is complete. The C++ stage will implement a client that speaks
the same external protocol, enabling interoperability between C++ and Python
applications through the shared RabbitMQ and Mosquitto brokers.

---

## How to Use This Documentation

Read the documents in this order:

| Order | Document | Purpose |
|---|---|---|
| 1 | `cpp-handoff.md` | Quick start — what's deployed, where files are, how to run Python reference |
| 2 | `protocol-spec.md` | External protocol — brokers, topics, queues, contracts, compatibility |
| 3 | `delivery-semantics.md` | Delivery guarantees, ACK semantics, bridge reliability |
| 4 | `command-protocol.md` | Command message structure, aliases, handler contract |
| 5 | `test-vectors.md` | Reference messages and integration test scenarios |
| 6 | `decisions-and-issues.md` | Architectural decisions, known issues, limitations |

---

## Key Facts at a Glance

| Item | Value |
|---|---|
| Project path | `/home/user/lab-amqp` |
| Python lab path | `/home/user/lab-amqp/python-lab` |
| RabbitMQ host:port | `127.0.0.1:5672` |
| RabbitMQ vhost | `/lab` |
| RabbitMQ user | `lab_user` |
| MQTT host:port | `127.0.0.1:1883` |
| MQTT user | `lab_user` |
| AMQP exchange | `lab.events` (direct, durable) |
| AMQP queues | `lab.heartbeat`, `lab.commands`, `lab.test` |
| AMQP routing keys | `heartbeat`, `command`, `test` |
| MQTT topics | `lab/heartbeat`, `lab/commands`, `lab/test` |
| MQTT QoS | 1 |
| Message types | `heartbeat` (v1), `command` (v1) |
| Command aliases | `status`, `restart_service`, `reload_config`, `get_metrics`, `ping` |
| Validation modes | `permissive`, `strict` |
| Python tests | 29 passed (24 unit + 5 integration) |

---

## Compatibility Matrix

The C++ client must be able to interoperate in both directions:

| Scenario | Direction | Status |
|---|---|---|
| C++ Publisher → Python Consumer | AMQP | Must work |
| Python Publisher → C++ Consumer | AMQP | Must work |
| C++ MQTT Publisher → Python Bridge | MQTT | Must work |
| Python MQTT Publisher → C++ Bridge/Consumer | MQTT | Must work (if bridge is C++) |

**Critical:** Do not modify the Python applications, the brokers, the queues,
the topics, or the external protocol. The C++ client must conform to the
existing protocol as specified in `protocol-spec.md`.

---

## Running the Python Reference for Comparison

```bash
cd /home/user/lab-amqp/python-lab

# Create .env from .env.example and fill in credentials
cp .env.example .env
# Edit .env with real values

# Activate virtualenv
source .venv/bin/activate

# Run unit tests (no brokers needed)
pytest tests/unit/

# Run integration tests (requires running brokers)
pytest tests/integration/

# Run individual applications
python -m lab_messaging.applications.mqtt_publisher --heartbeat
python -m lab_messaging.applications.amqp_consumer --queue lab.heartbeat
python -m lab_messaging.bridge.mqtt_to_amqp
```

Full chain test (3 terminals):

1. Terminal 1: `./scripts/run-amqp-consumer.sh --queue lab.heartbeat`
2. Terminal 2: `./scripts/run-bridge.sh`
3. Terminal 3: `./scripts/run-mqtt-publisher.sh --heartbeat`

---

## C++ Requirements Summary

| Requirement | Detail |
|---|---|
| OS | Linux (Debian 12 tested) |
| Build system | CMake (recommended) |
| C++ standard | C++17 or C++20 (to be decided) |
| AMQP | AMQP 0-9-1 compatible with RabbitMQ 4.3.8 |
| MQTT | MQTT compatible with Mosquitto 2.1.4 |
| JSON | UTF-8 encoded |
| No Python dependency | Must not link against Python |
| Graceful shutdown | Handle SIGINT/SIGTERM |
| Logging | Standard output with timestamps |

---

## Documents in This Package

| Document | Description |
|---|---|
| `cpp-handoff.md` | Quick start for the C++ agent |
| `protocol-spec.md` | External protocol specification |
| `delivery-semantics.md` | Delivery guarantees and reliability |
| `command-protocol.md` | Command message structure and aliases |
| `test-vectors.md` | Reference messages and test scenarios |
| `decisions-and-issues.md` | Architectural decisions and known issues |

---

## Success Criteria

A new agent in an empty chat, having access to this repository and the
`handoff-cpp/` documents, should be able to:

1. Read `cpp-handoff.md` and understand what's deployed
2. Read `protocol-spec.md` and implement the wire protocol
3. Read `test-vectors.md` and verify message compatibility
4. Build a C++ application that exchanges messages with the Python reference
5. Pass integration tests against the running brokers

---

## What NOT to Do

- Do NOT modify Python applications
- Do NOT modify broker configuration
- Do NOT change queue names, topic names, or routing keys
- Do NOT modify the JSON contract structure
- Do NOT start C++ development in this task (documentation only)
- Do NOT publish secrets or credentials

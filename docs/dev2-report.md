The Python Messaging Lab is complete. Here is the final report:
1. Working Machine Confirmation
- Hostname: lab-dockers
- FQDN: lab-dockers
- OS: Debian GNU/Linux 12 (bookworm)
- Architecture: x86_64
- User: user (uid=1000, docker group)
2. Infrastructure Fix
Mosquitto run.sh — The root cause was mosquitto_passwd -c -b being called unconditionally on every start. The -c flag creates a new password file and fails if the file already exists.
Fix: Wrap password generation in if [[ ! -f config/passwd ]]; then ... else ... fi. The file is created only on first start; subsequent starts preserve existing credentials.
Verified scenarios: first launch, repeat launch, stop/start, container restart, authentication with existing password — all pass without error.
RabbitMQ was left unchanged (existing config, credentials, and data volumes preserved).
3. Python Project Structure
/home/user/lab-amqp/python-lab/
├── pyproject.toml, .env.example, .gitignore, .python-version, uv.lock
├── src/lab_messaging/
│   ├── config/settings.py        # Central config from .env (no secrets logged)
│   ├── contracts/
│   │   ├── common.py             # Shared message structure
│   │   ├── heartbeat/v1.py       # Permissive validation
│   │   ├── heartbeat/v1_strict.py# Strict validation (Pydantic)
│   │   ├── command/v1.py         # Permissive validation
│   │   └── command/v1_strict.py  # Strict validation (Pydantic)
│   ├── mqtt/client.py            # Publisher + subscriber (paho-mqtt)
│   ├── amqp/client.py            # Publisher + consumer (pika, manual ACK)
│   ├── bridge/mqtt_to_amqp.py    # MQTT → AMQP bridge
│   ├── commands/dispatcher.py    # Handler table (no if/elif chains)
│   ├── commands/handlers/*.py    # 5 simulated handlers
│   ├── applications/             # 5 runner apps
│   └── utils/logging.py
├── scripts/                      # Runner + MQTT CLI scripts
├── tests/unit/                   # 24 tests (no brokers)
├── tests/integration/            # 5 tests (real brokers)
└── docs/                         # README, architecture, contracts, concepts, decisions, progress
4. Python Version
Python 3.11.2 (CPython, /usr/bin/python3.11)
5. Environment Management
uv (v0.13.9). Virtual environment at .venv/. uv.lock committed for reproducible builds.
6. Dependency Versions
Package	Version
pika	1.5.0
paho-mqtt	2.2.0
pydantic	2.14.4
pytest	8.4.2
pytest-mock	3.17.0
7. Application Architecture
MQTT Publisher ──MQTT──> Mosquitto ──MQTT──> Bridge ──AMQP──> RabbitMQ
                                                             │
                      AMQP Consumer ◄── queues ◄── exchange ──┘
                         (manual ACK, command dispatcher)
- Exchange: lab.events (direct, durable)
- Queues: lab.heartbeat, lab.commands (durable)
- Routing keys: heartbeat, command, test
- Messages: persistent (delivery_mode=2)
- Consumer ACK: manual
- Publisher Confirms: enabled
8. JSON Contracts
heartbeat v1: type, version(1), message_id, timestamp, payload{hostname, cpu_load, memory_used_percent, uptime_seconds}
command v1: type, version(1), message_id, timestamp, payload{alias, arguments}
Known aliases: status, restart_service, reload_config, get_metrics, ping
9. Validation Modes
Aspect	Permissive	Strict
Extra fields	Allowed	Forbidden
Type enforcement	Basic	Full (Pydantic)
Value constraints	None	Ranges, formats, known aliases
Implementation	Pure Python	Pydantic v2
Selection via VALIDATION_MODE env var. Business logic unchanged between modes.
10. Example Usage
# .env from .env.example, then fill real credentials
source .venv/bin/activate

# MQTT publisher/subscriber
./scripts/run-mqtt-publisher.sh --heartbeat
./scripts/run-mqtt-subscriber.sh --topic "lab/#"

# Full chain
./scripts/run-amqp-consumer.sh --queue lab.heartbeat &
./scripts/run-bridge.sh &
./scripts/run-mqtt-publisher.sh --heartbeat

# Interactive sender
./scripts/run-command-sender.sh
11. Test Results
29 passed (24 unit + 5 integration), 0 failed.
Unit tests cover: contract creation, serialization/deserialization, permissive/strict validation, unknown type/version, invalid JSON, dispatcher routing, unknown aliases.
Integration tests cover: MQTT direct pub/sub, AMQP direct publish/consume, full chain MQTT→Bridge→AMQP→Consumer (heartbeat, command, plain text).
12. Manual Scenarios Verified
- MQTT CLI pub/sub with UTF-8 (абракадабра)
- Python MQTT publisher/subscriber with JSON heartbeat
- Mosquitto repeatable start (no passwd error)
- Full chain: MQTT → Mosquitto → Bridge → RabbitMQ → Consumer
13. Known Limitations
- No exactly-once delivery guarantee between independent brokers
- Bridge message loss possible if RabbitMQ is down during publish
- Latency depends on clock synchronization between hosts
- Pika 1.x BlockingConnection deprecation warning (no impact on functionality)
- All command handlers are simulated only (no real system actions)
14. Ready for Next Stage
Yes, the laboratory is ready for the next independent C++ stage. All Python components are complete, tested, and documented. No C++ code or architecture was created in this stage.

Nemotron 3.5 Super VL 120B A12B


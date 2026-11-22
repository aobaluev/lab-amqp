# Progress

## Stage A — Infrastructure (complete)
- [x] Fixed mosquitto `run.sh` passwd file `-c` issue
- [x] Mosquitto starts repeatedly without error
- [x] RabbitMQ running and healthy
- [x] MQTT pub/sub verified
- [x] AMQP connectivity verified

## Stage B — Python Project Setup (complete)
- [x] Project structure created under `python-lab/`
- [x] `pyproject.toml` with dependencies (pika, paho-mqtt, pydantic, pytest)
- [x] `.env.example` and `.gitignore`
- [x] `uv` installed on stand
- [x] Python 3.11 virtual environment

## Stage C — MQTT Client (in progress)
- [ ] MQTT publisher
- [ ] MQTT subscriber
- [ ] Logging and graceful shutdown

## Stage D — JSON Contracts (planned)
- [ ] heartbeat v1 (permissive + strict)
- [ ] command v1 (permissive + strict)
- [ ] Validation mode selection

## Stage E — AMQP Client (planned)
- [ ] Publisher with Publisher Confirms
- [ ] Consumer with manual ACK
- [ ] Exchange, queues, routing keys

## Stage F — Bridge (planned)
- [ ] MQTT → AMQP forwarding
- [ ] Contract-based routing

## Stage G — Commands (planned)
- [ ] Command dispatcher
- [ ] Handlers (status, restart_service, reload_config, get_metrics, ping)
- [ ] Interactive command sender

## Stage H — Testing (planned)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual scenarios

## Stage I — Documentation (planned)
- [ ] README
- [ ] All docs

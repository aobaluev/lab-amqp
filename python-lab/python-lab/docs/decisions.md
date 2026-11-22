# Decisions

## Python 3.11 + uv

Chosen for reproducibility and performance. Python 3.11 is available on the
Debian 12 stand. `uv` provides fast, deterministic dependency resolution and
a lock file (`uv.lock`).

## No async frameworks

All components use synchronous, blocking I/O. This keeps the code
understandable and debuggable for a learning lab. `paho-mqtt` uses a
background thread for network I/O; `pika.BlockingConnection` is fully
synchronous.

## Separate permissive/strict validation modules

Rather than one module with conditional branches, `contracts/heartbeat/v1.py`
and `v1_strict.py` are independent modules with the same interface. Selection
happens at startup via `VALIDATION_MODE`; business logic never sees the
difference.

## No C++

This stage is Python-only. No C++ code, no C++ architecture sketches.

## No Docker for Python apps

Python applications run directly on the host. Only Mosquitto and RabbitMQ
run in Docker (from the previous stage).

## Manual ACK + Publisher Confirms

Chosen for reliability in a learning context. Manual ACK prevents message
loss on consumer crash; Publisher Confirms detect undeliverable messages.

## No exactly-once claim

Two independent brokers cannot provide exactly-once semantics without
distributed transactions. The lab documents this limitation.

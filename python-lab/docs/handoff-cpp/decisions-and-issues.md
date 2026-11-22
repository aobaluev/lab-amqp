# Decisions and Issues

This document records the significant architectural decisions made during the
Python stage of the `lab-amqp` laboratory, the problems encountered, and
recommendations for the C++ stage.

Status conventions:
- **IMPLEMENTED** — present in the Python code
- **VERIFIED** — confirmed by tests or manual runs
- **PARTIALLY VERIFIED** — confirmed in some scenarios only
- **KNOWN ISSUE** — known problem, not fixed
- **PLANNED** — discussed but not implemented
- **UNKNOWN** — could not be confirmed

---

## 1. Library Choices

| Decision | Detail | Status |
|---|---|---|
| Language | Python 3.11 | IMPLEMENTED, VERIFIED |
| Package manager | `uv` (with `uv.lock` for reproducibility) | IMPLEMENTED, VERIFIED |
| MQTT library | `paho-mqtt>=2.0.0,<3.0.0` | IMPLEMENTED, VERIFIED |
| AMQP library | `pika>=1.0.0,<2.0.0` | IMPLEMENTED, VERIFIED |
| Strict validation | `pydantic>=2.0.0,<3.0.0` | IMPLEMENTED, VERIFIED |
| Test framework | `pytest>=8.0.0,<9.0.0` | IMPLEMENTED, VERIFIED |
| Async frameworks | Not used (synchronous, blocking I/O only) | IMPLEMENTED, VERIFIED |
| C++ AMQP library | Not yet selected | PLANNED |
| C++ MQTT library | Not yet selected | PLANNED |
| C++ JSON library | Not yet selected | PLANNED |
| C++ build system | Not yet selected (CMake expected) | PLANNED |

**Reasoning for synchronous I/O:** Keeps code understandable and debuggable for a learning lab. `paho-mqtt` uses a background thread for network I/O; `pika.BlockingConnection` is fully synchronous.

---

## 2. MQTT QoS Choice

| Decision | Detail | Status |
|---|---|---|
| QoS level | 1 (at least once) | IMPLEMENTED, VERIFIED |
| Reasoning | Reliable delivery without the complexity of QoS 2 exactly-once | DECISION |
| Retain flag | `false` (not used) | IMPLEMENTED, VERIFIED |

**Trade-off:** QoS 1 guarantees at-least-once delivery, meaning duplicates are possible if the PUBACK is lost. This was accepted as a reasonable trade-off for a learning lab.

---

## 3. AMQP Acknowledgment Strategy

| Decision | Detail | Status |
|---|---|---|
| Consumer ACK | Manual ACK (`basic_ack` after processing) | IMPLEMENTED, VERIFIED |
| Publisher Confirms | `confirm_delivery()` enabled but not surfaced in pika 1.x app code | IMPLEMENTED, PARTIALLY VERIFIED |
| Durable queues | Yes | IMPLEMENTED, VERIFIED |
| Persistent messages | `delivery_mode=2` | IMPLEMENTED, VERIFIED |
| Dead-letter queue | Not configured | KNOWN ISSUE |
| Retry logic | Not implemented | KNOWN ISSUE |

**Reasoning:** Manual ACK prevents message loss on consumer crash. Publisher Confirms detect undeliverable messages (though pika 1.x limitation means the app code doesn't see confirmation results).

---

## 4. Message Format

| Decision | Detail | Status |
|---|---|---|
| Format | JSON | IMPLEMENTED, VERIFIED |
| Encoding | UTF-8 | IMPLEMENTED, VERIFIED |
| Timestamp | Epoch seconds (float64, 6 decimal places) | IMPLEMENTED, VERIFIED |
| Datetime | ISO-8601 UTC with `Z` suffix | IMPLEMENTED, VERIFIED |
| UUID | Standard UUID format | IMPLEMENTED, VERIFIED |

---

## 5. Contract Versioning

| Decision | Detail | Status |
|---|---|---|
| Version field | Per-message-type version (`type` + `version`) | IMPLEMENTED, VERIFIED |
| Current versions | heartbeat v1, command v1 | IMPLEMENTED, VERIFIED |
| Breaking change rule | New version number required | DECISION |
| Unknown version handling | Rejected with clear error, no crash | IMPLEMENTED, VERIFIED |

---

## 6. Validation Modes

| Decision | Detail | Status |
|---|---|---|
| Two modes | `permissive` and `strict` | IMPLEMENTED, VERIFIED |
| Permissive implementation | Pure Python, extra fields allowed | IMPLEMENTED, VERIFIED |
| Strict implementation | Pydantic 2.x, no extra fields, value constraints | IMPLEMENTED, VERIFIED |
| Mode selection | Via `VALIDATION_MODE` environment variable | IMPLEMENTED, VERIFIED |
| Business logic independence | Validation mode does not change business logic | IMPLEMENTED, VERIFIED |

---

## 7. Bridge Behavior

| Decision | Detail | Status |
|---|---|---|
| Direction | MQTT → AMQP only | IMPLEMENTED, VERIFIED |
| Topic-to-routing-key mapping | `lab/heartbeat`→`heartbeat`, `lab/commands`→`command`, `lab/test`→`test` | IMPLEMENTED, VERIFIED |
| Contract validation | According to `VALIDATION_MODE` | IMPLEMENTED, VERIFIED |
| Non-JSON passthrough | Arbitrary text passes through unchanged | IMPLEMENTED, VERIFIED |
| MQTT topic preservation | Stored in AMQP headers (`mqtt-topic`, `mqtt-qos`) | IMPLEMENTED, VERIFIED |
| Exactly-once claim | Not made | DECISION |
| Automatic reconnection | Not implemented | KNOWN ISSUE |

---

## 8. Logging

| Decision | Detail | Status |
|---|---|---|
| Logging framework | Python standard `logging` | IMPLEMENTED, VERIFIED |
| Log format | `%(asctime)s %(levelname)s %(name)s: %(message)s` | IMPLEMENTED, VERIFIED |
| Secret handling | Passwords never logged | IMPLEMENTED, VERIFIED |
| Payload logging | DEBUG level only, truncated to 200 chars | IMPLEMENTED, VERIFIED |
| Latency logging | `latency_ms` computed from message `timestamp` | IMPLEMENTED, VERIFIED |

---

## 9. Graceful Shutdown

| Decision | Detail | Status |
|---|---|---|
| Signals handled | SIGINT, SIGTERM | IMPLEMENTED, VERIFIED |
| Shutdown behavior | Stop accepting new messages, finish current processing, close connections | IMPLEMENTED, VERIFIED |
| `kill -9` | Not used as standard shutdown method | DECISION |
| `os._exit(0)` | Used after cleanup to force-terminate (background threads prevent clean `sys.exit()`) | IMPLEMENTED, VERIFIED |

---

## 10. Problems Discovered and Fixes

| Problem | Fix | Status |
|---|---|---|
| Mosquitto `run.sh` failed on repeat start because `mosquitto_passwd -c` refuses to overwrite existing passwd file | Wrap password generation in `if [[ ! -f config/passwd ]]; then ... fi` | FIXED, VERIFIED |
| `pika 1.x` `Basic.Deliver` has no `.queue` attribute | Pass queue name via closure instead of reading `method.queue` | FIXED, VERIFIED |
| `paho-mqtt 2.x` callback signatures changed (`rc` → `reason_code`, `reason_code` is enum not int) | Updated callbacks to match v2 API | FIXED, VERIFIED |
| `pika 1.x` `confirm_delivery()` takes no callback argument | Removed callback argument | FIXED, VERIFIED |
| `pika 1.x` `BlockingConnection` not thread-safe | Run `process_data_events()` on main thread, MQTT publish from separate thread in tests | FIXED, VERIFIED |
| `pika 1.x` `BasicProperties.timestamp` requires integer | Cast float timestamp to int for AMQP properties; keep float in JSON body | FIXED, VERIFIED |
| `signal.signal()` only works in main thread | Wrap in `try/except ValueError` | FIXED, VERIFIED |
| Bridge `run-bridge.sh` exited with code 0 but did nothing | Missing `if __name__ == "__main__":` block in bridge module | FIXED, VERIFIED |
| Bridge + consumer Ctrl+C caused "called on closed connection" errors | Added `_stopped` flag for idempotent `stop()`, signal handlers in `main()` with `os._exit(0)` | FIXED, VERIFIED |
| `pika.BlockingConnection` deprecation warning | Noted; migration to `Connection` adapter may be needed in future | KNOWN ISSUE |

---

## 11. Known Limitations (Python Stage)

| Limitation | Detail | Status |
|---|---|---|
| No exactly-once delivery | Two independent brokers cannot provide exactly-once without distributed transactions | KNOWN ISSUE |
| No automatic reconnection | Bridge and consumer exit on connection failure | KNOWN ISSUE |
| No dead-letter queue | Not configured | KNOWN ISSUE |
| No retry logic | Publisher does not retry on failure | KNOWN ISSUE |
| No message deduplication | Duplicate message_id accepted | KNOWN ISSUE |
| Latency depends on clock sync | Publisher and consumer clocks must be synchronized | KNOWN ISSUE |
| Command handlers are simulated only | No real system actions | DECISION |
| `pika.BlockingConnection` deprecation | Will be removed in pika 2.0 | KNOWN ISSUE |
| Publisher Confirms not surfaced in pika 1.x | App code cannot detect unroutable messages | KNOWN ISSUE |

---

## 12. Recommendations for C++ Stage

| Area | Recommendation |
|---|---|
| AMQP library | Choose a C++ AMQP 0-9-1 library (e.g., librabbitmq, cppamqp, or similar) |
| MQTT library | Choose a C++ MQTT library (e.g., Eclipse Paho MQTT C++, or similar) |
| JSON library | Choose a C++ JSON library (e.g., nlohmann/json, or similar) |
| Build system | CMake (expected) |
| C++ standard | C++17 or C++20 (to be decided) |
| Exactly-once | Do not attempt; document the limitation |
| Manual ACK | Implement manual acknowledgment |
| Durable queues | Declare queues as durable |
| Persistent messages | Set delivery_mode=2 |
| JSON contracts | Match the exact field names and types from `protocol-spec.md` |
| Validation modes | Implement both permissive and strict |
| Graceful shutdown | Handle SIGINT/SIGTERM with `os._exit`-equivalent (`std::_Exit` or `std::quick_exit`) |
| Signal handlers | Install in `main()`, not in library constructors |
| Thread safety | Be aware that blocking connection libraries may not be thread-safe |

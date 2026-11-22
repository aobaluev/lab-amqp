# Protocol Specification (Language-Independent)

This document defines the external messaging protocol used by the `lab-amqp`
laboratory. It is intentionally independent of any programming language or
implementation. A C++ client must conform to this specification to interoperate
with the existing Python applications and brokers.

Status conventions used in this document:
- **IMPLEMENTED** — present in the Python code
- **VERIFIED** — confirmed by tests or manual runs
- **PARTIALLY VERIFIED** — confirmed in some scenarios only
- **PLANNED** — discussed but not implemented
- **KNOWN ISSUE** — known problem, not fixed
- **UNKNOWN** — could not be confirmed

---

## 1. RabbitMQ (AMQP 0-9-1)

### 1.1 Broker Configuration

| Property | Value | Status |
|---|---|---|
| Broker image | `rabbitmq:4.3.8-management` | IMPLEMENTED, VERIFIED |
| Docker Compose project name | `lab-amqp-rabbitmq` | IMPLEMENTED, VERIFIED |
| Container name | `lab-amqp-rabbitmq` | IMPLEMENTED, VERIFIED |
| Hostname | `127.0.0.1` | IMPLEMENTED, VERIFIED |
| AMQP port | `5672` | IMPLEMENTED, VERIFIED |
| Management port | `15672` (localhost only via SSH tunnel) | IMPLEMENTED, VERIFIED |
| Virtual host | `/lab` | IMPLEMENTED, VERIFIED |
| Username | `lab_user` | IMPLEMENTED, VERIFIED |
| Password | Random hex (generated at first start, stored in `.env`) | IMPLEMENTED, VERIFIED |
| AMQP protocol version | AMQP 0-9-1 | IMPLEMENTED |

### 1.2 Exchange

| Property | Value | Status |
|---|---|---|
| Name | `lab.events` | IMPLEMENTED, VERIFIED |
| Type | `direct` | IMPLEMENTED, VERIFIED |
| Durable | `true` | IMPLEMENTED, VERIFIED |
| Auto-delete | `false` | IMPLEMENTED, VERIFIED |
| Internal | `false` | IMPLEMENTED, VERIFIED |

### 1.3 Queues

| Queue Name | Durable | Auto-delete | Exclusive | Purpose | Status |
|---|---|---|---|---|---|
| `lab.heartbeat` | `true` | `false` | `false` | Receives messages with routing key `heartbeat` | IMPLEMENTED, VERIFIED |
| `lab.commands` | `true` | `false` | `false` | Receives messages with routing key `command` | IMPLEMENTED, VERIFIED |
| `lab.test` | `true` | `false` | `false` | Receives messages with routing key `test` | IMPLEMENTED, VERIFIED |

### 1.4 Bindings

| Exchange | Queue | Routing Key | Status |
|---|---|---|---|
| `lab.events` | `lab.heartbeat` | `heartbeat` | IMPLEMENTED, VERIFIED |
| `lab.events` | `lab.commands` | `command` | IMPLEMENTED, VERIFIED |
| `lab.events` | `lab.test` | `test` | IMPLEMENTED, VERIFIED |

### 1.5 Message Properties

| Property | Type | Usage | Status |
|---|---|---|---|
| `content_type` | string | `"application/json"` for JSON, `"text/plain"` for raw text | IMPLEMENTED, VERIFIED |
| `message_id` | string | UUID, set by publisher | IMPLEMENTED, VERIFIED |
| `timestamp` | int64 (Unix seconds) | Set by publisher; from message `timestamp` field truncated to integer | IMPLEMENTED, VERIFIED |
| `delivery_mode` | int | `2` = persistent | IMPLEMENTED, VERIFIED |
| `correlation_id` | string | Optional, set by publisher if needed | IMPLEMENTED, VERIFIED |
| `headers` | table | `{"mqtt-topic": <topic>, "mqtt-qos": <qos>}` for bridged messages | IMPLEMENTED, VERIFIED |

### 1.6 Message Delivery Behavior

- Queues are **durable** (survive broker restart)
- Messages are **persistent** (`delivery_mode=2`, written to disk)
- Consumer uses **manual ACK** (`basic_ack` after successful processing)
- Publisher enables **Publisher Confirms** (`confirm_delivery()`), but pika 1.x does not surface confirmation callbacks to application code
- No dead-letter queue configured
- No retry logic in publisher
- No exactly-once delivery guarantee between independent brokers

---

## 2. MQTT (Mosquitto)

### 2.1 Broker Configuration

| Property | Value | Status |
|---|---|---|
| Broker image | `eclipse-mosquitto:2.1.4-alpine` | IMPLEMENTED, VERIFIED |
| Docker Compose project name | `lab-amqp-mosquitto` | IMPLEMENTED, VERIFIED |
| Container name | `lab-amqp-mosquitto` | IMPLEMENTED, VERIFIED |
| Hostname | `127.0.0.1` | IMPLEMENTED, VERIFIED |
| Port | `1883` | IMPLEMENTED, VERIFIED |
| MQTT protocol version | 5.0-compatible (mosquitto 2.x) | IMPLEMENTED, VERIFIED |
| Authentication | Username/password required (`allow_anonymous false`) | IMPLEMENTED, VERIFIED |
| Username | `lab_user` | IMPLEMENTED, VERIFIED |
| Password | Random hex (generated at first start, stored in `.env`) | IMPLEMENTED, VERIFIED |

### 2.2 Topics

| Topic | Purpose | Publisher | Subscriber | QoS | Retain | Status |
|---|---|---|---|---|---|---|
| `lab/heartbeat` | Heartbeat messages | MQTT Publisher, Bridge (inbound) | MQTT Subscriber, Bridge (outbound) | 1 | `false` | IMPLEMENTED, VERIFIED |
| `lab/commands` | Command messages | MQTT Publisher, Bridge (inbound) | MQTT Subscriber, Bridge (outbound) | 1 | `false` | IMPLEMENTED, VERIFIED |
| `lab/test` | Arbitrary text / raw JSON | MQTT Publisher, Bridge (inbound) | MQTT Subscriber, Bridge (outbound) | 1 | `false` | IMPLEMENTED, VERIFIED |
| `lab/#` | Wildcard for testing | N/A | MQTT Subscriber | 1 | `false` | IMPLEMENTED, VERIFIED |

### 2.3 MQTT Behavior

| Property | Value | Status |
|---|---|---|
| QoS level used | 1 (at least once) | IMPLEMENTED, VERIFIED |
| Retain flag | `false` (not used) | IMPLEMENTED, VERIFIED |
| Client ID | Auto-generated UUID prefix `lab-mqtt-<8 hex chars>` | IMPLEMENTED, VERIFIED |
| Persistent session | `false` (clean session) | IMPLEMENTED, VERIFIED |
| Keepalive | 60 seconds | IMPLEMENTED, VERIFIED |
| Reconnection | Manual reconnect logic in application | IMPLEMENTED, PARTIALLY VERIFIED |
| Offline message storage | Not applicable (clean session) | N/A |

### 2.4 Topic → Routing Key Table (Used by Bridge)

| MQTT Topic | AMQP Routing Key | Status |
|---|---|---|
| `lab/heartbeat` | `heartbeat` | IMPLEMENTED, VERIFIED |
| `lab/commands` | `command` | IMPLEMENTED, VERIFIED |
| `lab/test` | `test` | IMPLEMENTED, VERIFIED |

---

## 3. JSON Message Contracts

All messages are JSON objects encoded in UTF-8.

### 3.1 Common Message Structure

Every contract message (heartbeat or command) contains these top-level fields:

| Field | Type | Required | Description | Status |
|---|---|---|---|---|
| `type` | string | Yes | Message type: `"heartbeat"` or `"command"` | IMPLEMENTED, VERIFIED |
| `version` | integer | Yes | Contract version for this type (always `1`) | IMPLEMENTED, VERIFIED |
| `message_id` | string | Yes | Unique UUID | IMPLEMENTED, VERIFIED |
| `timestamp` | number (float) | Yes | Epoch seconds, up to 6 decimal places | IMPLEMENTED, VERIFIED |
| `datetime` | string | Yes | ISO-8601 UTC, format `YYYY-MM-DDTHH:MM:SSZ` | IMPLEMENTED, VERIFIED |
| `payload` | object | Yes | Type-specific data | IMPLEMENTED, VERIFIED |

### 3.2 Heartbeat v1

**Contract:** `type="heartbeat"`, `version=1`

**Example:**
```json
{
  "type": "heartbeat",
  "version": 1,
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T16:19:43Z",
  "payload": {
    "hostname": "lab-dockers",
    "cpu_load": 0.42,
    "memory_used_percent": 65.2,
    "uptime_seconds": 12000
  }
}
```

**Payload fields:**

| Field | Type | Constraints | Status |
|---|---|---|---|
| `hostname` | string | non-empty | IMPLEMENTED, VERIFIED |
| `cpu_load` | number | 0.0 – 1.0 (strict mode only) | IMPLEMENTED, VERIFIED |
| `memory_used_percent` | number | 0.0 – 100.0 (strict mode only) | IMPLEMENTED, VERIFIED |
| `uptime_seconds` | number | >= 0 (strict mode only) | IMPLEMENTED, VERIFIED |

**Validation behavior:**
- Permissive: required fields present, correct types, extra fields allowed
- Strict: all required fields, correct types, no extra fields, value range checks

---

### 3.3 Command v1

**Contract:** `type="command"`, `version=1`

**Example:**
```json
{
  "type": "command",
  "version": 1,
  "message_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T16:19:43Z",
  "payload": {
    "alias": "status",
    "arguments": {}
  }
}
```

**Payload fields:**

| Field | Type | Constraints | Status |
|---|---|---|---|
| `alias` | string | Must be one of: `status`, `restart_service`, `reload_config`, `get_metrics`, `ping` (strict mode only) | IMPLEMENTED, VERIFIED |
| `arguments` | object | Any JSON object | IMPLEMENTED, VERIFIED |

**Validation behavior:**
- Permissive: required fields present, correct types, extra fields allowed
- Strict: all required fields, correct types, no extra fields, alias must be known

---

### 3.4 Validation Modes

| Aspect | Permissive | Strict |
|---|---|---|
| Required fields | Must be present | Must be present |
| Field types | Must match | Must match |
| Extra fields | Allowed | Forbidden |
| Value ranges | Not enforced | Enforced (cpu_load 0-1, memory 0-100, uptime >= 0) |
| Alias validation | Not enforced | Must be known alias |
| Datetime format | Not validated | Must be valid ISO-8601 |
| Implementation | Pure Python | Pydantic 2.x |

**Selection:** Via `VALIDATION_MODE` environment variable (`permissive` or `strict`). Business logic does not change between modes.

---

### 3.5 Arbitrary Text Messages

Non-JSON text messages are supported on the `lab/test` topic and `test` routing key:

| Property | Value |
|---|---|
| Content-Type | `text/plain` |
| Encoding | UTF-8 |
| Contract | None — arbitrary text |
| Validation | None |
| Purpose | Testing arbitrary data transfer and latency measurement |

Text messages bypass JSON validation entirely and pass through the bridge unchanged.

---

## 4. Cross-Language Compatibility Requirements

Any C++ implementation must:

| Requirement | Specification |
|---|---|
| Character encoding | UTF-8 for all string fields |
| Timestamp | Epoch seconds as float64, up to 6 decimal places (e.g., `1795364383.843454`) |
| Datetime | ISO-8601 UTC with `Z` suffix (e.g., `2026-11-22T16:19:43Z`) |
| UUID | Standard UUID format (e.g., `550e8400-e29b-41d4-a716-446655440000`) |
| Numeric types | IEEE 754 double for float fields |
| JSON serialization | `json.dumps` equivalent with `ensure_ascii=False` |
| AMQP `content_type` | `"application/json"` for JSON, `"text/plain"` for text |
| AMQP `delivery_mode` | `2` (persistent) |
| MQTT payload encoding | UTF-8 |
| MQTT QoS | `1` |
| No Python concepts | Do not reference Pydantic, dataclasses, or Python-specific types in protocol |

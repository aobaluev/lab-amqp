# Command Protocol

This document defines the command message structure, command aliases, and
routing behavior used in the `lab-amqp` laboratory. All command messages are
JSON objects conforming to the command v1 contract.

---

## 1. Command Message Structure

A command message is a JSON message of type `"command"` with version `1`:

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | Must be `"command"` |
| `version` | integer | Yes | Must be `1` |
| `message_id` | string | Yes | Unique UUID |
| `timestamp` | number (float) | Yes | Epoch seconds, up to 6 decimal places |
| `datetime` | string | Yes | ISO-8601 UTC `YYYY-MM-DDTHH:MM:SSZ` |
| `payload` | object | Yes | Command-specific payload |

### 1.1 Payload Structure

| Field | Type | Required | Description |
|---|---|---|---|
| `alias` | string | Yes | Command alias (see section 2) |
| `arguments` | object | Yes | Command arguments (any JSON object, defaults to `{}`) |

**Example command message:**
```json
{
  "type": "command",
  "version": 1,
  "message_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T16:19:43Z",
  "payload": {
    "alias": "get_metrics",
    "arguments": {}
  }
}
```

---

## 2. Command Aliases

Five command aliases are defined. All handlers are **simulated/demo only** —
no real system actions are performed (no service restarts, no config changes,
no system commands).

| Alias | Purpose | Handler | Simulated Result | Status |
|---|---|---|---|---|
| `status` | Check service status | `handle_status` | `"All services nominal (simulated)"` | IMPLEMENTED, VERIFIED |
| `restart_service` | Simulate service restart | `handle_restart_service` | `"Service restart simulated (no actual restart)"` | IMPLEMENTED, VERIFIED |
| `reload_config` | Simulate config reload | `handle_reload_config` | `"Config reload simulated (no actual changes)"` | IMPLEMENTED, VERIFIED |
| `get_metrics` | Retrieve metrics | `handle_get_metrics` | `"Metrics: cpu=42% mem=65% (simulated)"` | IMPLEMENTED, VERIFIED |
| `ping` | Ping/pong test | `handle_ping` | `"pong"` | IMPLEMENTED, VERIFIED |

### 2.1 Handler Contract

Each handler:
- Receives `arguments` (a JSON object from the command payload)
- Returns a result dictionary (simulated data only)
- Must not perform real system actions
- Must not crash the consumer on error (exceptions are caught and logged)

### 2.2 Unknown Alias Behavior

If a command message contains an alias that is not in the table above:
- The dispatcher returns `{"status": "error", "error": "Unknown command alias: <alias>"}`
- The consumer does **not** crash
- The message is still ACKed (processing completed, even if the alias is unknown)

### 2.3 Invalid Message Behavior

If a command message is malformed (missing fields, wrong types, invalid JSON):
- Permissive validation: error raised with clear message, message not dispatched
- Strict validation: error raised with detailed field-level errors
- Consumer logs the error and continues processing other messages

---

## 3. Routing

| Source Topic | AMQP Routing Key | Queue | Status |
|---|---|---|---|
| `lab/commands` (MQTT) | `command` | `lab.commands` | IMPLEMENTED, VERIFIED |
| Direct AMQP publish | `command` | `lab.commands` | IMPLEMENTED, VERIFIED |

Commands are published to the `lab.events` exchange with routing key `command`,
and consumed from the `lab.commands` queue.

---

## 4. Dispatch Table (External Contract)

The dispatcher uses an explicit mapping from alias string to handler function.
The C++ implementation should use an equivalent mapping (e.g., `std::map<std::string, HandlerFunc>`).

| Alias | Handler Function (Python) | C++ Equivalent |
|---|---|---|
| `status` | `handle_status(arguments)` | `handle_status(arguments)` |
| `restart_service` | `handle_restart_service(arguments)` | `handle_restart_service(arguments)` |
| `reload_config` | `handle_reload_config(arguments)` | `handle_reload_config(arguments)` |
| `get_metrics` | `handle_get_metrics(arguments)` | `handle_get_metrics(arguments)` |
| `ping` | `handle_ping(arguments)` | `handle_ping(arguments)` |

**Important:** The C++ implementation must not import or depend on the Python
dispatcher module. It must implement its own alias-to-handler mapping that
produces the same external behavior.

---

## 5. Command Examples

### 5.1 Status Command
```json
{
  "type": "command",
  "version": 1,
  "message_id": "uuid-here",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T16:19:43Z",
  "payload": {
    "alias": "status",
    "arguments": {}
  }
}
```

### 5.2 Ping Command
```json
{
  "type": "command",
  "version": 1,
  "message_id": "uuid-here",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T16:19:43Z",
  "payload": {
    "alias": "ping",
    "arguments": {}
  }
}
```

### 5.3 Get Metrics Command with Arguments
```json
{
  "type": "command",
  "version": 1,
  "message_id": "uuid-here",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T16:19:43Z",
  "payload": {
    "alias": "get_metrics",
    "arguments": {
      "detailed": true
    }
  }
}
```

### 5.4 Unknown Alias (should not crash)
```json
{
  "type": "command",
  "version": 1,
  "message_id": "uuid-here",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T16:19:43Z",
  "payload": {
    "alias": "nonexistent",
    "arguments": {}
  }
}
```
Expected result: error response, message still ACKed.

---

## 6. Safety Rules

| Rule | Reason |
|---|---|
| No real system restarts | Lab is for learning only |
| No real config changes | Prevent accidental system modification |
| No shell command execution | Security and safety |
| All handlers return simulated data only | No side effects |
| Unknown aliases return error, not crash | Consumer must remain available |
| Invalid JSON does not crash consumer | Robustness requirement |

# Message Contracts

JSON contracts define the structure of messages exchanged in the lab.
Each message type has its own version.

## Common Structure

All messages share these top-level fields:

| Field | Type | Description |
|---|---|---|
| `type` | string | Message type (`heartbeat`, `command`) |
| `version` | integer | Contract version for this type |
| `message_id` | string | Unique message identifier (UUID) |
| `timestamp` | string | ISO-8601 UTC timestamp |
| `payload` | object | Type-specific data |

## Heartbeat v1

```json
{
  "type": "heartbeat",
  "version": 1,
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-11-22T10:00:00Z",
  "payload": {
    "hostname": "lab-dockers",
    "cpu_load": 0.42,
    "memory_used_percent": 65.2,
    "uptime_seconds": 12000
  }
}
```

### Payload fields

| Field | Type | Constraints |
|---|---|---|
| `hostname` | string | non-empty |
| `cpu_load` | number | 0.0 – 1.0 (strict mode) |
| `memory_used_percent` | number | 0.0 – 100.0 (strict mode) |
| `uptime_seconds` | number | >= 0 (strict mode) |

## Command v1

```json
{
  "type": "command",
  "version": 1,
  "message_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2026-11-22T10:00:00Z",
  "payload": {
    "alias": "status",
    "arguments": {}
  }
}
```

### Payload fields

| Field | Type | Constraints |
|---|---|---|
| `alias` | string | one of: status, restart_service, reload_config, get_metrics, ping |
| `arguments` | object | any JSON object |

## Versioning Rules

- `type` identifies the message category
- `version` identifies the contract version for that type
- Backward-incompatible changes require a new `version` number
- Unknown types or versions are rejected with a clear error, not a crash

## Validation Modes

### Permissive

Required fields must be present with correct types. Additional fields are
allowed. Suitable for forward-compatible systems.

### Strict

All required fields present, correct types, no additional fields, values
must satisfy constraints (ranges, formats, known aliases). Implemented with
Pydantic.

Switch between modes via `VALIDATION_MODE` environment variable. Business
logic does not change.

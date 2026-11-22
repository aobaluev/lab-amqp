# Test Vectors

This document provides reference messages and integration test scenarios for
verifying C++ client compatibility with the existing `lab-amqp` laboratory.

All JSON examples use UTF-8 encoding.

---

## 1. Unit Test Vectors (No Brokers Required)

These can be verified by a C++ implementation without any running brokers.

### TV-1: Valid Heartbeat v1 (Permissive)

**Input:**
```json
{
  "type": "heartbeat",
  "version": 1,
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T10:00:00Z",
  "payload": {
    "hostname": "lab-dockers",
    "cpu_load": 0.42,
    "memory_used_percent": 65.2,
    "uptime_seconds": 12000
  }
}
```

**Expected result:** Message accepted.

**Permissive validation:** Accepted.
**Strict validation:** Accepted.

---

### TV-2: Valid Command v1 (Permissive)

**Input:**
```json
{
  "type": "command",
  "version": 1,
  "message_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": 1795364383.843454,
  "datetime": "2026-11-22T10:00:00Z",
  "payload": {
    "alias": "status",
    "arguments": {}
  }
}
```

**Expected result:** Message accepted.

**Permissive validation:** Accepted.
**Strict validation:** Accepted.

---

### TV-3: Heartbeat with Extra Payload Field

**Input:** Same as TV-1, but `payload` includes `"custom_field": "extra info"`.

**Expected result:**
- Permissive: Accepted (extra fields allowed)
- Strict: Rejected (extra fields forbidden)

---

### TV-4: Missing Required Field (`cpu_load`)

**Input:** Valid heartbeat v1 but `payload.cpu_load` is missing.

**Expected result:** Rejected with error indicating missing field.

**Permissive validation:** Rejected.
**Strict validation:** Rejected.

---

### TV-5: Wrong Type (`cpu_load` is string instead of number)

**Input:** Valid heartbeat v1 but `payload.cpu_load` is `"0.42"` (string).

**Expected result:** Rejected with error indicating type mismatch.

**Permissive validation:** Rejected.
**Strict validation:** Rejected.

---

### TV-6: Unknown Message Type

**Input:** `{"type": "unknown", "version": 1, ...}`

**Expected result:** Rejected with error indicating invalid type.

**Permissive validation:** Rejected.
**Strict validation:** Rejected.

---

### TV-7: Unknown Contract Version

**Input:** `{"type": "heartbeat", "version": 99, ...}`

**Expected result:** Rejected with error indicating invalid version.

**Permissive validation:** Rejected.
**Strict validation:** Rejected.

---

### TV-8: Invalid JSON

**Input:** `{not valid json}`

**Expected result:** Rejected with parse error.

**Permissive validation:** Rejected.
**Strict validation:** Rejected.

---

### TV-9: Command with Unknown Alias (Strict)

**Input:** Command message with `payload.alias = "nonexistent"`.

**Expected result:**
- Permissive: Accepted (alias not validated in permissive mode)
- Strict: Rejected (alias must be one of: status, restart_service, reload_config, get_metrics, ping)

---

### TV-10: Out-of-Range Value (Strict)

**Input:** Heartbeat with `payload.cpu_load = 1.5` (> 1.0).

**Expected result:**
- Permissive: Accepted (no range checks)
- Strict: Rejected (cpu_load must be 0.0–1.0)

---

### TV-11: Duplicate Message ID

**Input:** Same `message_id` sent twice.

**Expected result:** Both accepted (no deduplication in current implementation).
**Note:** Deduplication is NOT implemented in the Python lab. C++ should not implement it unless required.

---

## 2. Integration Test Scenarios (Requires Running Brokers)

These require Mosquitto on `127.0.0.1:1883` and RabbitMQ on `127.0.0.1:5672`,
vhost `/lab`, user `lab_user`.

### IV-1: MQTT Publish/Subscribe Direct

**Steps:**
1. Subscribe to `lab/test` with QoS 1
2. Publish `"hello mqtt"` to `lab/test` with QoS 1
3. Verify subscriber receives the message

**Expected:** Subscriber receives `"hello mqtt"` with topic `lab/test`, QoS 1.

---

### IV-2: AMQP Publish/Consume Direct

**Steps:**
1. Create temp queue bound to `lab.events` with routing key `test`
2. Consume from temp queue with manual ACK
3. Publish `{"test": "unique-id"}` to `lab.events` with routing key `test`
4. Verify consumer receives the message and ACKs it

**Expected:** Consumer receives 1 message, ACKs it, message content matches.

---

### IV-3: Full Chain — MQTT → Bridge → RabbitMQ → Consumer

**Steps:**
1. Start AMQP consumer on `lab.heartbeat` queue
2. Start MQTT → AMQP Bridge
3. Publish heartbeat v1 JSON to MQTT topic `lab/heartbeat`
4. Verify consumer receives the message on `lab.heartbeat`

**Expected:** Consumer receives the heartbeat message with `type=heartbeat`, `version=1`.

---

### IV-4: Full Chain — Command

**Steps:**
1. Start AMQP consumer on `lab.commands` queue
2. Start MQTT → AMQP Bridge
3. Publish command v1 JSON (alias=`status`) to MQTT topic `lab/commands`
4. Verify consumer receives the message on `lab.commands`

**Expected:** Consumer receives the command message with `type=command`, `payload.alias=status`.

---

### IV-5: Full Chain — Plain Text

**Steps:**
1. Create temp queue bound to `lab.events` with routing key `test`
2. Start AMQP consumer on temp queue
3. Start MQTT → AMQP Bridge
4. Publish `"plain text message"` to MQTT topic `lab/test`
5. Verify consumer receives the text on temp queue

**Expected:** Consumer receives `"plain text message"` with `content_type=text/plain`.

---

### IV-6: Broker Unavailable

**Steps:**
1. Stop Mosquitto container
2. Attempt MQTT publish
3. Verify error is logged, no crash

**Expected:** Publisher logs connection error and exits gracefully (or retries if implemented).

---

### IV-7: Connection Recovery

**Steps:**
1. Start Mosquitto after it was stopped
2. Attempt MQTT publish/subscribe
3. Verify connection succeeds

**Expected:** Connection established normally after broker restart.

---

### IV-8: Consumer Crash During Processing

**Steps:**
1. Start AMQP consumer on `lab.heartbeat`
2. Publish a heartbeat message
3. Kill consumer process (SIGKILL) before it ACKs
4. Restart consumer
5. Verify message is redelivered

**Expected:** Message is redelivered to the restarted consumer (no ACK was sent).

---

### IV-9: Latency Measurement

**Steps:**
1. Publish 10 heartbeat messages with timestamps
2. Consumer calculates latency = receive_time - message_timestamp
3. Report min, max, avg latency

**Expected:** Latency values in milliseconds, positive numbers. Note: depends on clock synchronization between publisher and consumer hosts.

---

## 3. Test Fixtures (Machine-Readable JSON)

Create the following files in `python-lab/tests/fixtures/`:

| File | Description |
|---|---|
| `valid_heartbeat_v1.json` | TV-1 |
| `valid_command_v1.json` | TV-2 |
| `heartbeat_with_extra.json` | TV-3 |
| `missing_cpu_load.json` | TV-4 |
| `wrong_type_cpu_load.json` | TV-5 |
| `unknown_type.json` | TV-6 |
| `unknown_version.json` | TV-7 |
| `invalid_json.txt` | TV-8 |
| `command_unknown_alias.json` | TV-9 |
| `cpu_load_out_of_range.json` | TV-10 |
| `duplicate_message_id_1.json` | TV-11 (first) |
| `duplicate_message_id_2.json` | TV-11 (second, same message_id) |

**Note:** The fixtures directory does not exist yet in the Python project. It should be created as part of the C++ stage test setup.

---

## 4. Expected Behaviors Summary

| Scenario | Permissive | Strict |
|---|---|---|
| Valid message | Accepted | Accepted |
| Extra field in payload | Accepted | Rejected |
| Missing required field | Rejected | Rejected |
| Wrong field type | Rejected | Rejected |
| Unknown message type | Rejected | Rejected |
| Unknown contract version | Rejected | Rejected |
| Invalid JSON | Rejected | Rejected |
| Unknown command alias | Accepted | Rejected |
| Out-of-range numeric value | Accepted | Rejected |
| Duplicate message_id | Accepted | Accepted |

# Delivery Semantics

This document describes the actual delivery guarantees and reliability behavior
of the `lab-amqp` laboratory. It covers RabbitMQ (AMQP), MQTT (Mosquitto), and
the MQTT → AMQP Bridge.

Status conventions:
- **IMPLEMENTED** — present in the Python code
- **VERIFIED** — confirmed by tests or manual runs
- **PARTIALLY VERIFIED** — confirmed in some scenarios only
- **KNOWN ISSUE** — known problem, not fixed
- **UNKNOWN** — could not be confirmed

---

## 1. RabbitMQ (AMQP 0-9-1)

### 1.1 Publisher Confirmation

| Question | Answer | Status |
|---|---|---|
| When does Publisher consider publication successful? | When `basic_publish()` returns without exception. In pika 1.x, `basic_publish` returns `None`; confirmation callbacks are registered but not surfaced to application code. | IMPLEMENTED, VERIFIED |
| Are Publisher Confirms used? | `confirm_delivery()` is called on the channel, but pika 1.x does not invoke the delivery confirmation callback in application code. The publish is treated as successful if no exception is raised. | IMPLEMENTED, PARTIALLY VERIFIED |
| What happens if connection is lost during publish? | `basic_publish` raises an exception; application catches and logs it. Message may or may not have reached the broker. | IMPLEMENTED, PARTIALLY VERIFIED |

### 1.2 Consumer Acknowledgment

| Question | Answer | Status |
|---|---|---|
| When does Consumer send ACK? | After `basic_consume` callback returns and `basic_ack(delivery_tag=...)` is called explicitly (manual ACK mode). | IMPLEMENTED, VERIFIED |
| What happens if Consumer crashes before ACK? | RabbitMQ redelivers the message to another consumer (or the same one after reconnect) because no ACK was sent. | IMPLEMENTED, VERIFIED |
| What happens if Consumer closes connection before ACK? | The unacknowledged message is requeued by RabbitMQ. | IMPLEMENTED, PARTIALLY VERIFIED |
| Is automatic ACK supported? | Yes, via `--auto-ack` flag, but manual ACK is the default and recommended mode. | IMPLEMENTED, VERIFIED |

### 1.3 Error Handling

| Question | Answer | Status |
|---|---|---|
| What happens if handler raises exception? | Exception is caught, logged as ERROR, message is still ACKed (consumer does not crash). | IMPLEMENTED, VERIFIED |
| Can a message be NACKed/requeued? | `basic_nack()` method exists in AMQPClient but is not used by the consumer application. | IMPLEMENTED, UNUSED |
| Is there retry logic? | No retry logic in publisher or consumer. | KNOWN ISSUE |
| Is there a dead-letter queue? | No dead-letter queue configured. | KNOWN ISSUE |
| Are messages durable? | Yes: durable queues + `delivery_mode=2` persistent messages. | IMPLEMENTED, VERIFIED |

### 1.4 Two Types of Confirmation

| Type | Direction | Meaning | Implementation |
|---|---|---|---|
| Publisher Confirm | Broker → Publisher | Broker accepted the message into the exchange/queue | `confirm_delivery()` enabled but not surfaced in pika 1.x app code |
| Consumer ACK | Consumer → Broker | Consumer successfully processed the message | `basic_ack()` called manually after processing |

These are independent: a message can be Publisher Confirmed but not yet Consumer Acked, and vice versa.

---

## 2. MQTT (Mosquitto)

### 2.1 QoS Guarantees

| QoS Level | Guarantee | Used in Lab? | Status |
|---|---|---|---|
| 0 | At most once (fire and forget) | No | N/A |
| 1 | At least once (acknowledged via PUBACK) | Yes | IMPLEMENTED, VERIFIED |
| 2 | Exactly once | No | N/A |

QoS 1 means: message is delivered at least once. Duplicates are possible if the PUBACK is lost.

### 2.2 Connection Behavior

| Question | Answer | Status |
|---|---|---|
| Behavior on connection loss | Client logs warning; application must manually reconnect | IMPLEMENTED, PARTIALLY VERIFIED |
| Persistent sessions | Clean session (`false` persistence) — no offline message storage | IMPLEMENTED, VERIFIED |
| Client ID influence | Auto-generated UUID-based ID; no persistent session tied to ID | IMPLEMENTED, VERIFIED |
| Offline subscriber messages | Not stored (clean session); messages published while subscriber is offline are lost | IMPLEMENTED, VERIFIED |
| Repeated delivery (QoS 1) | Possible if PUBACK is lost; subscriber may receive duplicates | IMPLEMENTED, PARTIALLY VERIFIED |

### 2.3 Message Storage

- No retained messages (`retain=false`)
- No persistent session storage
- Messages published while no subscriber is connected are dropped by the broker

---

## 3. MQTT → AMQP Bridge Reliability

The Bridge is a boundary between two independent brokers. Its behavior:

| Scenario | Behavior | Status |
|---|---|---|
| Bridge receives MQTT message | Logs it, parses JSON if applicable, determines routing key | IMPLEMENTED, VERIFIED |
| Bridge publishes to AMQP | Calls `basic_publish()` with `mandatory=True`; treats as successful if no exception | IMPLEMENTED, VERIFIED |
| Bridge checks AMQP publication success | No explicit confirmation check (pika 1.x limitation); logs publish attempt | IMPLEMENTED, PARTIALLY VERIFIED |
| RabbitMQ unavailable during publish | Exception caught and logged; message is lost for this delivery | IMPLEMENTED, VERIFIED |
| Bridge crashes between MQTT receive and AMQP publish | MQTT message is lost (no ACK sent back to MQTT broker for redelivery; QoS 1 PUBACK not sent until publish completes) | IMPLEMENTED, PARTIALLY VERIFIED |
| Bridge reconnection | Not implemented as automatic reconnection loop; application exits on connection failure | KNOWN ISSUE |

### 3.1 Delivery Guarantees Summary

| Guarantee | Provided? | Reason |
|---|---|---|
| At-most-once (MQTT side) | Partial | QoS 1 with PUBACK after AMQP publish; if publish fails, no PUBACK → redelivery possible |
| At-least-once (MQTT side) | Partial | Same as above; duplicates possible |
| Exactly-once | **No** | Two independent brokers cannot provide exactly-once without distributed transactions |
| No message loss | **No** | Bridge message loss possible if RabbitMQ is down during publish |
| No duplication | **No** | Possible on QoS 1 if PUBACK is lost |

**The Bridge does not claim exactly-once delivery.**

### 3.2 Guarantees NOT Provided

| Missing Guarantee | Status |
|---|---|
| Exactly-once delivery | KNOWN ISSUE |
| Automatic reconnection on Bridge | KNOWN ISSUE |
| Dead-letter queue | KNOWN ISSUE |
| Publisher retry on failure | KNOWN ISSUE |
| Message deduplication | KNOWN ISSUE |

---

## 4. End-to-End Delivery Summary

| Path | Reliability | Notes |
|---|---|---|
| MQTT Publisher → Mosquitto | At-least-once (QoS 1) | Duplicates possible on PUBACK loss |
| Mosquitto → Bridge | At-least-once (QoS 1) | Duplicates possible |
| Bridge → RabbitMQ | Best-effort | Message lost if RabbitMQ down |
| RabbitMQ → Consumer | At-least-once (manual ACK) | Redelivery if no ACK before crash |
| Full chain (MQTT → Consumer) | At-least-once | Duplicates possible at multiple points |

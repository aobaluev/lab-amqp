# Concepts

Brief explanations of key messaging concepts, tied to the implemented code.

## MQTT Topic

A UTF-8 string used by Mosquitto to route messages. Publishers send to a
topic; subscribers express interest in a topic. Topics can use wildcards:
`+` matches one level, `#` matches multiple levels.

In this lab: `lab/heartbeat`, `lab/commands`, `lab/test`.

## MQTT QoS

Quality of Service levels:
- **0** — at most once (fire and forget)
- **1** — at least once (acknowledged delivery)
- **2** — exactly once (not used in this lab)

The lab uses QoS 1 by default for reliable delivery.

## AMQP Exchange

An exchange receives messages from producers and routes them to queues based
on routing rules. In this lab we use a **direct exchange** named `lab.events`.

## Routing Key

A string attached to a message by the publisher. The exchange matches it
against queue bindings. In this lab:
- `heartbeat` → `lab.heartbeat` queue
- `command` → `lab.commands` queue
- `test` → (no queue bound by default; create a temp queue for testing)

## Queue

A buffer in RabbitMQ that stores messages until consumers process them.
Queues in this lab are **durable** (survive broker restart).

## ACK (Acknowledgment)

Consumer confirms to RabbitMQ that a message was successfully processed.
- **Manual ACK** (used in this lab): consumer calls `basic_ack` after
  processing. If the consumer crashes before ACK, RabbitMQ redelivers.
- **Automatic ACK**: RabbitMQ removes the message immediately after delivery.

## Publisher Confirms

RabbitMQ confirms to the publisher that a message was accepted by the
exchange (and routed to a queue). This is different from consumer ACK:
Publisher Confirms = broker → publisher; Consumer ACK = consumer → broker.

## Durable Queue

A queue that survives broker restarts. Non-durable queues are deleted when
RabbitMQ stops.

## Persistent Message

A message written to disk by RabbitMQ (delivery_mode=2). Survives broker
restart. Combined with durable queues, this provides message durability.

## JSON Contract

A versioned schema for JSON messages. Each message type has its own contract
version. Enables structured, evolvable message exchange.

## Schema Validation

Checking that an incoming message matches its contract. Two modes:
- **Permissive**: required fields + types only, extras allowed
- **Strict**: full schema, no extras, value constraints

## Graceful Shutdown

On SIGINT/SIGTERM, applications stop accepting new messages, finish current
processing, close connections, and exit cleanly. No `kill -9`.

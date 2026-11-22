# Architecture

## Overview

The Python lab consists of small, standalone applications communicating through
two message brokers: Mosquitto (MQTT) and RabbitMQ (AMQP).

## Components

### MQTT Publisher (`applications/mqtt_publisher.py`)
Connects to Mosquitto, publishes JSON or plain text messages to a topic.
Supports heartbeat v1 and command v1 contract generation.

### MQTT Subscriber (`applications/mqtt_subscriber.py`)
Connects to Mosquitto, subscribes to a topic, prints incoming messages with
metadata (topic, QoS, message_id, type, version, latency).

### AMQP Publisher (`applications/amqp_publisher.py`)
Connects to RabbitMQ, publishes to the `lab.events` direct exchange with
routing keys `heartbeat`, `command`, or `test`. Uses Publisher Confirms.

### AMQP Consumer (`applications/amqp_consumer.py`)
Consumes from `lab.heartbeat` or `lab.commands` queues with manual ACK.
Dispatches command messages to registered handlers.

### Bridge (`bridge/mqtt_to_amqp.py`)
Subscribes to MQTT topics (`lab/heartbeat`, `lab/commands`, `lab/test`),
forwards to RabbitMQ with appropriate routing keys. Validates JSON contracts
according to configured mode (permissive/strict).

### Command Sender (`applications/command_sender.py`)
Interactive text-menu application for sending heartbeat, command, and plain
text messages via AMQP.

### Command Dispatcher (`commands/dispatcher.py`)
Routes command aliases to handler functions via an explicit dict table.
Handlers are isolated in separate modules under `commands/handlers/`.

## Data Flow

```
MQTT Publisher ──MQTT──> Mosquitto ──MQTT──> Bridge ──AMQP──> RabbitMQ
                                                                       │
                              AMQP Consumer ◄── queues ◄── exchange ──┘
```

## Reliability

- Queues are durable
- Messages are persistent (delivery_mode=2)
- Consumer uses manual ACK
- Publisher uses Publisher Confirms
- Bridge does not claim exactly-once delivery

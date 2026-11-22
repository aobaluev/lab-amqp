"""MQTT Publisher application.

Publishes messages to a Mosquitto broker. Supports JSON and plain text.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from lab_messaging.config.settings import Settings
from lab_messaging.contracts import (
    VALIDATION_MODES,
    get_command_module,
    get_heartbeat_module,
)
from lab_messaging.contracts.command import COMMAND_V1_ALIASES  # type: ignore
from lab_messaging.mqtt.client import (
    MQTTClient,
    current_timestamp,
    current_datetime,
    generate_message_id,
)

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def publish_heartbeat(client: MQTTClient, validation_mode: str) -> None:
    """Create and publish a heartbeat v1 message."""
    mod = get_heartbeat_module(validation_mode)
    ts = current_timestamp()
    dt = current_datetime()
    msg = mod.make_heartbeat(
        message_id=generate_message_id(),
        timestamp=ts,
        datetime=dt,
        hostname="lab-dockers",
        cpu_load=0.42,
        memory_used_percent=65.2,
        uptime_seconds=12000,
    )
    payload = mod.serialize(msg)
    client.publish("lab/heartbeat", payload, qos=1)
    logger.info("Published heartbeat message_id=%s", msg["message_id"])


def publish_command(client: MQTTClient, alias: str, validation_mode: str) -> None:
    """Create and publish a command v1 message."""
    mod = get_command_module(validation_mode)
    ts = current_timestamp()
    dt = current_datetime()
    msg = mod.make_command(
        message_id=generate_message_id(),
        timestamp=ts,
        datetime=dt,
        alias=alias,
        arguments={},
    )
    payload = mod.serialize(msg)
    client.publish("lab/commands", payload, qos=1)
    logger.info("Published command alias=%s message_id=%s", alias, msg["message_id"])


def publish_text(client: MQTTClient, text: str) -> None:
    """Publish arbitrary plain text."""
    client.publish("lab/test", text, qos=1)
    logger.info("Published text: %s", text[:100])


def publish_json(client: MQTTClient, json_str: str) -> None:
    """Publish raw JSON text."""
    # Validate it's parseable
    json.loads(json_str)
    client.publish("lab/test", json_str, qos=1)
    logger.info("Published JSON: %s", json_str[:100])


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT Publisher")
    parser.add_argument("--topic", default="lab/test", help="MQTT topic")
    parser.add_argument("--message", default="hello mqtt", help="Message text")
    parser.add_argument("--json", action="store_true", help="Treat message as JSON")
    parser.add_argument("--heartbeat", action="store_true", help="Publish heartbeat v1")
    parser.add_argument("--command", choices=COMMAND_V1_ALIASES, help="Publish command alias")
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2], help="QoS level")
    parser.add_argument("--count", type=int, default=1, help="Number of messages to publish")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval between messages (seconds)")
    parser.add_argument("--validation-mode", choices=VALIDATION_MODES, default="permissive", help="Validation mode")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args()

    setup_logging(args.log_level)

    settings = Settings()
    client = MQTTClient(settings)
    try:
        client.connect()

        for i in range(args.count):
            if args.heartbeat:
                publish_heartbeat(client, args.validation_mode)
            elif args.command:
                publish_command(client, args.command, args.validation_mode)
            elif args.json:
                publish_json(client, args.message)
            else:
                publish_text(client, args.message)

            if i < args.count - 1:
                time.sleep(args.interval)

        logger.info("Publisher finished, sent %d message(s)", args.count)
    finally:
        client.stop()


if __name__ == "__main__":
    main()
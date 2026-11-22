"""AMQP Publisher application.

Publishes messages to RabbitMQ via the lab.events exchange.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from lab_messaging.amqp.client import (
    AMQPClient,
    ROUTING_KEY_COMMAND,
    ROUTING_KEY_HEARTBEAT,
    ROUTING_KEY_TEST,
)
from lab_messaging.config.settings import Settings
from lab_messaging.contracts import (
    VALIDATION_MODES,
    get_command_module,
    get_heartbeat_module,
)
from lab_messaging.contracts.command import COMMAND_V1_ALIASES  # type: ignore
from lab_messaging.mqtt.client import (
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


def publish_heartbeat(client: AMQPClient, validation_mode: str) -> None:
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
    client.publish(
        routing_key=ROUTING_KEY_HEARTBEAT,
        body=payload,
        content_type="application/json",
        message_id=msg["message_id"],
    )
    logger.info("Published heartbeat message_id=%s", msg["message_id"])


def publish_command(client: AMQPClient, alias: str, validation_mode: str) -> None:
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
    client.publish(
        routing_key=ROUTING_KEY_COMMAND,
        body=payload,
        content_type="application/json",
        message_id=msg["message_id"],
    )
    logger.info("Published command alias=%s message_id=%s", alias, msg["message_id"])


def publish_text(client: AMQPClient, text: str) -> None:
    client.publish(
        routing_key=ROUTING_KEY_TEST,
        body=text,
        content_type="text/plain",
    )
    logger.info("Published text: %s", text[:100])


def main() -> None:
    parser = argparse.ArgumentParser(description="AMQP Publisher")
    parser.add_argument("--routing-key", default="test", help="AMQP routing key")
    parser.add_argument("--message", default="hello amqp", help="Message text")
    parser.add_argument("--json", action="store_true", help="Treat message as JSON")
    parser.add_argument("--heartbeat", action="store_true", help="Publish heartbeat v1")
    parser.add_argument("--command", choices=COMMAND_V1_ALIASES, help="Publish command alias")
    parser.add_argument("--count", type=int, default=1, help="Number of messages")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval (seconds)")
    parser.add_argument("--validation-mode", choices=VALIDATION_MODES, default="permissive", help="Validation mode")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args()

    setup_logging(args.log_level)

    settings = Settings()
    client = AMQPClient(settings)
    try:
        client.connect()

        for i in range(args.count):
            if args.heartbeat:
                publish_heartbeat(client, args.validation_mode)
            elif args.command:
                publish_command(client, args.command, args.validation_mode)
            elif args.json:
                json.loads(args.message)
                client.publish(
                    routing_key=args.routing_key,
                    body=args.message,
                    content_type="application/json",
                )
                logger.info("Published JSON")
            else:
                publish_text(client, args.message)

            if i < args.count - 1:
                time.sleep(args.interval)

        logger.info("Publisher finished, sent %d message(s)", args.count)
    finally:
        client.stop()


if __name__ == "__main__":
    main()
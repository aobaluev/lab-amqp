"""AMQP Consumer application.

Consumes messages from RabbitMQ queues with manual ACK and logs
latency for JSON messages.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone

from lab_messaging.amqp.client import (
    AMQPClient,
    QUEUE_COMMANDS,
    QUEUE_HEARTBEAT,
)
from lab_messaging.config.settings import Settings
from lab_messaging.commands.dispatcher import dispatcher
from lab_messaging.commands.handlers import (
    get_metrics,
    ping,
    reload_config,
    restart_service,
    status,
)

logger = logging.getLogger(__name__)

stats = {
    "received": 0,
    "acked": 0,
    "latencies": [],
}


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def register_handlers() -> None:
    """Register all demo command handlers with the dispatcher."""
    dispatcher.register("status", status.handle_status)
    dispatcher.register("restart_service", restart_service.handle_restart_service)
    dispatcher.register("reload_config", reload_config.handle_reload_config)
    dispatcher.register("get_metrics", get_metrics.handle_get_metrics)
    dispatcher.register("ping", ping.handle_ping)
    logger.info("Registered %d command handlers", len(dispatcher.aliases))


def on_amqp_message(
    queue_name: str,
    channel,
    method,
    properties,
    body: bytes,
) -> None:
    """Handle incoming AMQP message (business logic only, no ACK)."""
    stats["received"] += 1
    delivery_tag = method.delivery_tag
    routing_key = method.routing_key

    message_id = properties.message_id if properties and properties.message_id else "unknown"
    timestamp = properties.timestamp if properties and properties.timestamp else None

    logger.info(
        "AMQP message received queue=%s routing_key=%s delivery_tag=%s message_id=%s",
        queue_name,
        routing_key,
        delivery_tag,
        message_id,
    )

    # Compute latency from message timestamp
    latency_ms = None
    if timestamp:
        try:
            msg_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            latency_ms = (now - msg_time).total_seconds() * 1000
            stats["latencies"].append(latency_ms)
            logger.info("  latency_ms=%.2f", latency_ms)
        except (ValueError, OSError):
            logger.warning("  Invalid timestamp: %s", timestamp)

    # Try to parse as JSON
    try:
        text = body.decode("utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            msg_type = data.get("type", "unknown")
            msg_version = data.get("version", "unknown")
            payload = data.get("payload", {})
            logger.info("  type=%s version=%s", msg_type, msg_version)
            logger.debug("  payload=%s", json.dumps(payload, ensure_ascii=False)[:200])

            # If it's a command, dispatch it
            if msg_type == "command":
                alias = payload.get("alias", "unknown")
                arguments = payload.get("arguments", {})
                result = dispatcher.dispatch(alias, arguments)
                logger.info("  dispatch result=%s", result["status"])

    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.debug("  text=%s", body[:200])


def print_stats() -> None:
    """Print statistics."""
    print("\n=== Statistics ===")
    print(f"Received: {stats['received']}")
    print(f"Acked: {stats['acked']}")
    if stats["latencies"]:
        lats = sorted(stats["latencies"])
        print(f"Min latency: {min(lats):.2f} ms")
        print(f"Max latency: {max(lats):.2f} ms")
        print(f"Avg latency: {sum(lats) / len(lats):.2f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="AMQP Consumer")
    parser.add_argument("--queue", default="lab.heartbeat", help="Queue to consume")
    parser.add_argument("--auto-ack", action="store_true", help="Use automatic ACK")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args()
    print(args)

    setup_logging(args.log_level)

    settings = Settings()
    client = AMQPClient(settings)

    try:
        client.connect()
        register_handlers()

        auto_ack = args.auto_ack

        def callback(ch, method, props, body):
            on_amqp_message(args.queue, ch, method, props, body)
            if not auto_ack:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                stats["acked"] += 1

        logger.info("Consumer running on queue=%s. Press Ctrl+C to stop.", args.queue)
        client.consume(args.queue, callback, auto_ack=auto_ack)
    finally:
        print_stats()
        client.stop()


if __name__ == "__main__":
    main()
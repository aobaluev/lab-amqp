"""AMQP Consumer application.

Consumes messages from RabbitMQ queues with manual ACK and logs
latency for JSON messages.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from lab_messaging.amqp.client import (
    AMQPClient,
    QUEUE_COMMANDS,
    QUEUE_HEARTBEAT,
    QUEUE_TEST,
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
    detailed: bool = False,
) -> None:
    """Handle incoming AMQP message (business logic only, no ACK)."""
    stats["received"] += 1
    delivery_tag = method.delivery_tag
    routing_key = method.routing_key

    message_id = properties.message_id if properties and properties.message_id else "unknown"

    logger.info(
        "AMQP message received queue=%s routing_key=%s delivery_tag=%s message_id=%s",
        queue_name,
        routing_key,
        delivery_tag,
        message_id,
    )

    # Decode body for display
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = f"<binary {len(body)} bytes>"

    # Always show message content (truncated for readability)
    display_text = text[:300] + ("..." if len(text) > 300 else "")
    logger.info("  body=%s", display_text)

    # Detailed mode: show raw unprocessed message first
    if detailed:
        logger.info("  raw_body=%s", text)

    # Parse JSON to extract timestamp/datetime and dispatch commands
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            msg_type = data.get("type", "unknown")
            msg_version = data.get("version", "unknown")
            payload = data.get("payload", {})
            msg_timestamp = data.get("timestamp")
            msg_datetime = data.get("datetime")
            logger.info("  type=%s version=%s", msg_type, msg_version)
            logger.debug("  payload=%s", json.dumps(payload, ensure_ascii=False)[:200])

            # Compute latency from epoch timestamp in message
            latency_ms = None
            if isinstance(msg_timestamp, (int, float)):
                try:
                    msg_time = datetime.fromtimestamp(msg_timestamp, tz=timezone.utc)
                    now = datetime.now(timezone.utc)
                    latency_ms = (now - msg_time).total_seconds() * 1000
                    stats["latencies"].append(latency_ms)
                    logger.info("  latency_ms=%.2f", latency_ms)
                except (ValueError, OSError):
                    logger.warning("  Invalid epoch timestamp: %s", msg_timestamp)

            # Show human-readable datetime from message
            if isinstance(msg_datetime, str):
                logger.info("  datetime=%s", msg_datetime)

            # If it's a command, dispatch it
            if msg_type == "command":
                alias = payload.get("alias", "unknown")
                arguments = payload.get("arguments", {})
                result = dispatcher.dispatch(alias, arguments)
                logger.info("  dispatch result=%s", result["status"])

    except (json.JSONDecodeError, UnicodeDecodeError):
        pass  # body already logged above as plain text


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
    parser.add_argument("--queue", default="lab.heartbeat,lab.commands,lab.test", help="Queue(s) to consume (comma-separated)")
    parser.add_argument("--auto-ack", action="store_true", help="Use automatic ACK")
    parser.add_argument("--detailed", action="store_true", help="Show raw unprocessed message body first")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args()

    setup_logging(args.log_level)

    settings = Settings()
    client = AMQPClient(settings)

    def _signal_handler(signum, frame) -> None:
        logger.info("Received signal %s, shutting down consumer...", signum)
        client.stop()
        os._exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        client.connect()
        register_handlers()

        auto_ack = args.auto_ack

        queues = [q.strip() for q in args.queue.split(",")]

        def make_callback(qname: str):
            def callback(ch, method, props, body):
                on_amqp_message(qname, ch, method, props, body, detailed=args.detailed)
                if not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    stats["acked"] += 1
            return callback

        client._channel.basic_qos(prefetch_count=1)
        for qname in queues:
            client._channel.basic_consume(
                queue=qname,
                on_message_callback=make_callback(qname),
                auto_ack=auto_ack,
            )
            logger.info("Consumer subscribed queue=%s", qname)

        queues_str = ", ".join(queues)
        logger.info("Consumer running on queues=%s. Press Ctrl+C to stop.", queues_str)

        # Use process_data_events loop for reliable message delivery.
        # pika BlockingConnection's start_consuming() can miss consumer
        # callbacks; process_data_events() is the reliable polling approach.
        try:
            while client._running:
                client._connection.process_data_events(time_limit=1)
        except (KeyboardInterrupt, OSError):
            pass
    finally:
        print_stats()
        client.stop()
    os._exit(0)


if __name__ == "__main__":
    main()
"""Interactive command sender application.

Provides a text-menu UI for sending:
- Ready-made heartbeat JSON messages
- Command alias messages (status, restart_service, reload_config, get_metrics, ping)
- Arbitrary plain text

Sends via RabbitMQ AMQP exchange.

Can be used interactively (no arguments) or as a console utility
with CLI arguments for non-interactive sending.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
import uuid

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
from lab_messaging.contracts.command import COMMAND_V1_ALIASES
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


def print_header(title: str) -> None:
    print(f"\n{'=' * 35}")
    print(f"{title}")
    print(f"{'=' * 35}")


def send_heartbeat(client: AMQPClient, validation_mode: str) -> None:
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
    print(f"  [OK] Heartbeat sent (message_id={msg['message_id']})")
    logger.info("Sent heartbeat message_id=%s", msg["message_id"])


def send_command(client: AMQPClient, alias: str, validation_mode: str) -> None:
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
    print(f"  [OK] Command '{alias}' sent (message_id={msg['message_id']})")
    logger.info("Sent command alias=%s message_id=%s", alias, msg["message_id"])


def send_text(client: AMQPClient, text: str) -> None:
    client.publish(
        routing_key=ROUTING_KEY_TEST,
        body=text,
        content_type="text/plain",
    )
    print(f"  [OK] Text sent: {text[:80]}")
    logger.info("Sent text message")


def command_aliases_menu(client: AMQPClient, validation_mode: str) -> None:
    """Interactive submenu for command aliases."""
    aliases = [
        ("1", "status"),
        ("2", "restart_service"),
        ("3", "reload_config"),
        ("4", "get_metrics"),
        ("5", "ping"),
    ]

    while True:
        print_header("COMMAND ALIASES")
        for num, alias in aliases:
            print(f"  {num}. {alias}")
        print("  0. Back")

        choice = input("\nSelect command (1-5, 0=back): ").strip()
        if choice == "0":
            break
        for num, alias in aliases:
            if choice == num:
                send_command(client, alias, validation_mode)
                break
        else:
            print("  Invalid selection.")


def main_menu(client: AMQPClient, validation_mode: str) -> None:
    """Main interactive menu."""
    while True:
        print_header("LAB AMQP MESSAGE SENDER")
        print("  1. Send heartbeat")
        print("  2. Send sample JSON")
        print("  3. Send custom text")
        print("  4. Command aliases")
        print("  5. Exit")

        choice = input("\nSelect (1-5): ").strip()

        if choice == "1":
            send_heartbeat(client, validation_mode)
        elif choice == "2":
            ts = current_timestamp()
            dt = current_datetime()
            sample = json.dumps(
                {
                    "type": "heartbeat",
                    "version": 1,
                    "message_id": generate_message_id(),
                    "timestamp": ts,
                    "datetime": dt,
                    "payload": {
                        "hostname": "lab-dockers",
                        "cpu_load": 0.42,
                        "memory_used_percent": 65.2,
                        "uptime_seconds": 12000,
                    },
                },
                ensure_ascii=False,
            )
            print(f"  JSON: {sample}")
            client.publish(
                routing_key=ROUTING_KEY_HEARTBEAT,
                body=sample,
                content_type="application/json",
            )
            print("  [OK] Sample JSON sent")
        elif choice == "3":
            text = input("  Enter message: ").strip()
            if text:
                send_text(client, text)
        elif choice == "4":
            command_aliases_menu(client, validation_mode)
        elif choice == "5":
            print("  Goodbye.")
            break
        else:
            print("  Invalid selection.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lab AMQP message sender")
    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Send heartbeat v1 message",
    )
    parser.add_argument(
        "--command",
        choices=COMMAND_V1_ALIASES,
        help="Send command alias message",
    )
    parser.add_argument(
        "--text",
        help="Send arbitrary plain text",
    )
    parser.add_argument(
        "--json",
        help="Send raw JSON string",
    )
    parser.add_argument(
        "--routing-key",
        default="test",
        help="AMQP routing key (default: test)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of messages to send (default: 1)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Interval between messages in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--validation-mode",
        choices=VALIDATION_MODES,
        default="permissive",
        help="Validation mode (default: permissive)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Log level (default: INFO)",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)

    settings = Settings()
    client = AMQPClient(settings)

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    try:
        client.connect()

        # Bind a temporary queue for the "test" routing key so that
        # sample JSON and custom text messages are not returned as unroutable.
        test_queue = f"lab.command.sender.test.{uuid.uuid4().hex[:8]}"
        client._channel.queue_declare(queue=test_queue, durable=True, auto_delete=True)
        client._channel.queue_bind(
            exchange="lab.events", queue=test_queue, routing_key=ROUTING_KEY_TEST
        )
        logger.info("Bound temp queue=%s for routing_key=test", test_queue)

        # Non-interactive mode: CLI arguments provided
        if args.heartbeat:
            for i in range(args.count):
                send_heartbeat(client, args.validation_mode)
                if i < args.count - 1:
                    time.sleep(args.interval)
        elif args.command:
            for i in range(args.count):
                send_command(client, args.command, args.validation_mode)
                if i < args.count - 1:
                    time.sleep(args.interval)
        elif args.text:
            for i in range(args.count):
                send_text(client, args.text)
                if i < args.count - 1:
                    time.sleep(args.interval)
        elif args.json:
            # Validate JSON
            json.loads(args.json)
            for i in range(args.count):
                client.publish(
                    routing_key=args.routing_key,
                    body=args.json,
                    content_type="application/json",
                )
                if i < args.count - 1:
                    time.sleep(args.interval)
        else:
            # Interactive mode: no CLI arguments
            main_menu(client, args.validation_mode)
    finally:
        client.stop()


if __name__ == "__main__":
    main()
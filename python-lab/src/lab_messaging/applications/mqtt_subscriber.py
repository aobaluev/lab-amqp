"""MQTT Subscriber application.

Subscribes to MQTT topics and prints incoming messages with metadata
including latency for JSON messages.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone

from lab_messaging.config.settings import Settings
from lab_messaging.mqtt.client import MQTTClient

logger = logging.getLogger(__name__)

stats = {
    "received": 0,
    "latencies": [],
}


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def on_message(topic: str, payload: bytes, qos: int) -> None:
    """Handle incoming MQTT message."""
    stats["received"] += 1

    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = "<binary>"

    print(f"\n[MQTT MESSAGE] topic={topic} qos={qos} size={len(payload)}")

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            message_id = data.get("message_id", "unknown")
            msg_type = data.get("type", "unknown")
            msg_version = data.get("version", "unknown")
            timestamp = data.get("timestamp")

            print(f"  type={msg_type}")
            print(f"  version={msg_version}")
            print(f"  message_id={message_id}")
            print(f"  timestamp={timestamp}")

            if timestamp:
                try:
                    msg_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    latency_ms = (now - msg_time).total_seconds() * 1000
                    stats["latencies"].append(latency_ms)
                    print(f"  latency_ms={latency_ms:.2f}")
                except (ValueError, AttributeError):
                    print("  latency_ms=n/a (invalid timestamp)")

            print(f"  payload={json.dumps(data.get('payload', {}), ensure_ascii=False)[:200]}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(f"  text={text[:200]}")

    print()


def print_stats() -> None:
    """Print statistics about received messages."""
    if stats["received"] == 0:
        print("\nNo messages received.")
        return

    print("\n=== Statistics ===")
    print(f"Received: {stats['received']}")
    if stats["latencies"]:
        lats = sorted(stats["latencies"])
        print(f"Min latency: {min(lats):.2f} ms")
        print(f"Max latency: {max(lats):.2f} ms")
        print(f"Avg latency: {sum(lats) / len(lats):.2f} ms")
        p50 = lats[len(lats) // 2]
        p95 = lats[int(len(lats) * 0.95)] if len(lats) > 20 else lats[-1]
        print(f"p50 latency: {p50:.2f} ms")
        print(f"p95 latency: {p95:.2f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT Subscriber")
    parser.add_argument("--topic", default="lab/#", help="MQTT topic or wildcard")
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2], help="QoS level")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args()

    setup_logging(args.log_level)

    settings = Settings()
    client = MQTTClient(settings)
    client.set_message_handler(on_message)

    try:
        client.connect()
        client.subscribe(args.topic, qos=args.qos)
        logger.info("Subscriber running on topic=%s. Press Ctrl+C to stop.", args.topic)
        client.loop_forever()
    finally:
        print_stats()
        client.stop()


if __name__ == "__main__":
    main()
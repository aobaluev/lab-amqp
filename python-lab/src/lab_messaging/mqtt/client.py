"""MQTT client using paho-mqtt.

Provides a simple synchronous MQTT publisher and subscriber with
logging, graceful shutdown, and JSON contract support.
"""

from __future__ import annotations

import json
import logging
import signal
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from lab_messaging.config.settings import Settings

logger = logging.getLogger(__name__)


class MQTTClient:
    """A synchronous MQTT client wrapper around paho-mqtt.

    Handles connect, publish, subscribe, and graceful shutdown on
    SIGINT/SIGTERM. Not asyncio-based — uses paho's blocking loop.
    """

    def __init__(self, settings: Settings, client_id: Optional[str] = None) -> None:
        self.settings = settings
        self.client_id = client_id or f"lab-mqtt-{uuid.uuid4().hex[:8]}"
        self._client: Optional[mqtt.Client] = None
        self._running = False
        self._loop_started = False

        # Install signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        logger.info("Received signal %s, shutting down...", signum)
        self.stop()

    def connect(self) -> None:
        """Connect to the MQTT broker."""
        kwargs = self.settings.mqtt_connect_kwargs()
        host = kwargs["host"]
        port = kwargs["port"]
        user = kwargs["username"]

        logger.info(
            "MQTT connecting host=%s port=%s user=%s",
            host,
            port,
            user,
        )

        self._client = mqtt.Client(client_id=self.client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self._client.username_pw_set(kwargs["username"], kwargs["password"])

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish
        self._client.on_subscribe = self._on_subscribe
        self._client.on_message = self._on_message

        self._client.connect(host, port, keepalive=60)
        self._client.loop_start()
        self._loop_started = True

        # Wait for connection
        deadline = time.time() + 10
        while not self._running and time.time() < deadline:
            time.sleep(0.1)

        if not self._running:
            raise RuntimeError("MQTT connection timeout")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code == 0:
            self._running = True
            logger.info(
                "MQTT connected host=%s port=%s rc=%s",
                self.settings.mqtt_host,
                self.settings.mqtt_port,
                reason_code,
            )
        else:
            logger.error("MQTT connection failed rc=%s", reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None) -> None:
        self._running = False
        if reason_code != 0:
            logger.warning("MQTT unexpected disconnect rc=%s", reason_code)
        else:
            logger.info("MQTT disconnected")

    def _on_publish(self, client, userdata, mid, reason_code, properties=None) -> None:
        logger.debug("MQTT published mid=%s", mid)

    def _on_subscribe(self, client, userdata, mid, reason_code, properties=None) -> None:
        logger.info("MQTT subscribed mid=%s qos=%s", mid, reason_code)

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage) -> None:
        """Default message handler — logs the message. Override via set_message_handler."""
        self._handle_message(msg.topic, msg.payload, msg.qos)

    def _handle_message(self, topic: str, payload: bytes, qos: int) -> None:
        """Process an incoming MQTT message."""
        logger.info(
            "MQTT message received topic=%s qos=%s size=%d",
            topic,
            qos,
            len(payload),
        )

        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            text = "<binary>"

        logger.debug("MQTT payload topic=%s payload=%s", topic, text[:200])

        # Try to parse as JSON for latency and contract info
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                message_id = data.get("message_id", "unknown")
                msg_type = data.get("type", "unknown")
                msg_version = data.get("version", "unknown")
                timestamp = data.get("timestamp")

                latency_ms = None
                if timestamp:
                    try:
                        msg_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        now = datetime.now(timezone.utc)
                        latency_ms = (now - msg_time).total_seconds() * 1000
                    except (ValueError, AttributeError):
                        pass

                logger.info(
                    "MQTT JSON message topic=%s message_id=%s type=%s version=%s latency_ms=%s",
                    topic,
                    message_id,
                    msg_type,
                    msg_version,
                    f"{latency_ms:.2f}" if latency_ms is not None else "n/a",
                )
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("MQTT non-JSON message topic=%s", topic)

    def set_message_handler(self, handler: Callable[[str, bytes, int], None]) -> None:
        """Set a custom message handler callback."""
        self._handle_message = handler

    def publish(self, topic: str, payload: str | bytes, qos: int = 1, retain: bool = False) -> None:
        """Publish a message to the given topic."""
        if not self._running or self._client is None:
            raise RuntimeError("MQTT client not connected")

        if isinstance(payload, str):
            payload_bytes = payload.encode("utf-8")
        else:
            payload_bytes = payload

        logger.info(
            "MQTT publish topic=%s qos=%s size=%d retain=%s",
            topic,
            qos,
            len(payload_bytes),
            retain,
        )

        result = self._client.publish(topic, payload_bytes, qos=qos, retain=retain)
        result.wait_for_publish(timeout=5)
        logger.debug("MQTT publish confirmed topic=%s mid=%s", topic, result.mid)

    def subscribe(self, topic: str, qos: int = 1) -> None:
        """Subscribe to the given topic."""
        if not self._running or self._client is None:
            raise RuntimeError("MQTT client not connected")

        logger.info("MQTT subscribe topic=%s qos=%s", topic, qos)
        result, mid = self._client.subscribe(topic, qos=qos)
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT subscribe failed with code {result}")

    def stop(self) -> None:
        """Stop the client and disconnect gracefully."""
        self._running = False
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error during MQTT disconnect: %s", exc)
            self._client = None
        self._loop_started = False
        logger.info("MQTT client stopped")

    def loop_forever(self) -> None:
        """Block until stop() is called."""
        if not self._running:
            raise RuntimeError("MQTT client not connected")
        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def current_timestamp() -> str:
    """Return current UTC timestamp in ISO-8601 format with Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_message_id() -> str:
    """Generate a UUID-based message ID."""
    return str(uuid.uuid4())
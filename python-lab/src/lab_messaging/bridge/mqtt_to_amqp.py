"""MQTT → AMQP Bridge.

Subscribes to MQTT topics and forwards messages to RabbitMQ using
appropriate routing keys. Non-JSON payloads pass through unchanged.
"""

from __future__ import annotations

import json
import logging
import signal
import time
from typing import Optional

import paho.mqtt.client as mqtt

from lab_messaging.amqp.client import (
    AMQPClient,
    EXCHANGE_NAME,
    ROUTING_KEY_COMMAND,
    ROUTING_KEY_HEARTBEAT,
    ROUTING_KEY_TEST,
)
from lab_messaging.config.settings import Settings
from lab_messaging.contracts import VALIDATION_MODES, get_command_module, get_heartbeat_module

logger = logging.getLogger(__name__)

# MQTT topic → AMQP routing key mapping
TOPIC_ROUTING_MAP = {
    "lab/heartbeat": ROUTING_KEY_HEARTBEAT,
    "lab/commands": ROUTING_KEY_COMMAND,
    "lab/test": ROUTING_KEY_TEST,
}


class Bridge:
    """Bridge between Mosquitto (MQTT) and RabbitMQ (AMQP).

    Subscribes to MQTT topics, determines the message type/version from
    JSON payloads when possible, and forwards to AMQP with the correct
    routing key. Non-JSON messages pass through as-is.
    """

    def __init__(self, settings: Settings, validation_mode: str = "permissive") -> None:
        if validation_mode not in VALIDATION_MODES:
            raise ValueError(
                f"Invalid validation mode '{validation_mode}'. Must be one of {VALIDATION_MODES}"
            )
        self.settings = settings
        self.validation_mode = validation_mode

        self._mqtt_client: Optional[mqtt.Client] = None
        self._amqp_client: Optional[AMQPClient] = None
        self._running = False

        self._heartbeat_mod = get_heartbeat_module(validation_mode)
        self._command_mod = get_command_module(validation_mode)

# Install signal handlers for graceful shutdown (main thread only)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # signal handlers can only be installed in the main thread
            pass

    def _signal_handler(self, signum, frame) -> None:
        logger.info("Received signal %s, shutting down bridge...", signum)
        self.stop()

    def connect(self) -> None:
        """Connect to both MQTT and AMQP brokers."""
        # Connect AMQP first
        self._amqp_client = AMQPClient(self.settings)
        self._amqp_client.connect()

        # Connect MQTT
        self._mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        kwargs = self.settings.mqtt_connect_kwargs()
        self._mqtt_client.username_pw_set(kwargs["username"], kwargs["password"])

        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self._mqtt_client.on_message = self._on_mqtt_message

        logger.info(
            "Bridge MQTT connecting host=%s port=%s user=%s",
            kwargs["host"],
            kwargs["port"],
            kwargs["username"],
        )
        self._mqtt_client.connect(kwargs["host"], kwargs["port"], keepalive=60)
        self._mqtt_client.loop_start()

        # Wait for MQTT connection
        deadline = time.time() + 10
        while not self._running and time.time() < deadline:
            time.sleep(0.1)

        if not self._running:
            raise RuntimeError("Bridge MQTT connection timeout")

        logger.info("Bridge connected to both brokers")

    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == 0:
            self._running = True
            logger.info("Bridge MQTT connected rc=%s", rc)
            # Subscribe to all mapped topics
            for topic in TOPIC_ROUTING_MAP:
                client.subscribe(topic, qos=1)
                logger.info("Bridge subscribed MQTT topic=%s", topic)
        else:
            logger.error("Bridge MQTT connection failed rc=%s", rc)

    def _on_mqtt_disconnect(self, client, userdata, flags, rc, properties=None) -> None:
        self._running = False
        if rc != 0:
            logger.warning("Bridge MQTT unexpected disconnect rc=%s", rc)
        else:
            logger.info("Bridge MQTT disconnected")

    def _on_mqtt_message(self, client, userdata, msg: mqtt.MQTTMessage) -> None:
        """Handle incoming MQTT message and forward to AMQP."""
        topic = msg.topic
        routing_key = TOPIC_ROUTING_MAP.get(topic)

        if routing_key is None:
            logger.warning("Bridge no AMQP route for MQTT topic=%s", topic)
            return

        payload_bytes = msg.payload
        payload_str: Optional[str] = None

        try:
            payload_str = payload_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("Bridge non-UTF-8 payload on topic=%s, skipping", topic)
            return

        logger.info(
            "Bridge MQTT message topic=%s qos=%s size=%d routing_key=%s",
            topic,
            msg.qos,
            len(payload_bytes),
            routing_key,
        )

        # Try to parse as JSON and determine contract type/version
        headers = {"mqtt-topic": topic, "mqtt-qos": str(msg.qos)}
        message_id = None
        timestamp = None
        content_type = "text/plain"

        try:
            data = json.loads(payload_str)
            if isinstance(data, dict):
                message_id = data.get("message_id")
                timestamp = data.get("timestamp")
                msg_type = data.get("type")
                msg_version = data.get("version")

                logger.info(
                    "Bridge JSON message topic=%s type=%s version=%s message_id=%s",
                    topic,
                    msg_type,
                    msg_version,
                    message_id,
                )

                # Validate according to configured mode
                if msg_type == "heartbeat" and msg_version == 1:
                    self._heartbeat_mod.validate(data)
                    content_type = "application/json"
                elif msg_type == "command" and msg_version == 1:
                    self._command_mod.validate(data)
                    content_type = "application/json"
                elif msg_type in ("heartbeat", "command"):
                    logger.warning(
                        "Bridge unknown version: type=%s version=%s",
                        msg_type,
                        msg_version,
                    )
                    # Still forward — validation mode determines strictness
                    content_type = "application/json"
                else:
                    content_type = "application/json"

        except (json.JSONDecodeError, ValueError) as exc:
            # Not valid JSON or validation failed — forward as plain text
            logger.warning(
                "Bridge non-JSON or validation failed topic=%s error=%s, forwarding as text",
                topic,
                exc,
            )
            content_type = "text/plain"

        # Forward to AMQP
        try:
            self._amqp_client.publish(
                routing_key=routing_key,
                body=payload_str,
                content_type=content_type,
                message_id=str(message_id) if message_id else None,
                headers=headers,
            )
            logger.info(
                "Bridge forwarded topic=%s routing_key=%s message_id=%s",
                topic,
                routing_key,
                message_id,
            )
        except Exception as exc:
            logger.error(
                "Bridge AMQP publish failed routing_key=%s error=%s",
                routing_key,
                exc,
            )
            # Do not ack / do not raise — the MQTT loop continues.
            # The message is lost for this delivery; reconnection logic
            # handles broker recovery.

    def run_forever(self) -> None:
        """Block until stop() is called."""
        if not self._running:
            raise RuntimeError("Bridge not connected")
        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the bridge and disconnect from both brokers."""
        self._running = False
        if self._mqtt_client is not None:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error stopping MQTT client: %s", exc)
            self._mqtt_client = None
        if self._amqp_client is not None:
            self._amqp_client.stop()
            self._amqp_client = None
        logger.info("Bridge stopped")
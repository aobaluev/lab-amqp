"""AMQP client using pika.

Provides a simple synchronous AMQP publisher and consumer with
manual ACK, persistent messages, durable queues, and Publisher Confirms.
"""

from __future__ import annotations

import json
import logging
import signal
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

import pika

from lab_messaging.config.settings import Settings

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "lab.events"
EXCHANGE_TYPE = "direct"

QUEUE_HEARTBEAT = "lab.heartbeat"
QUEUE_COMMANDS = "lab.commands"
QUEUE_TEST = "lab.test"

ROUTING_KEY_HEARTBEAT = "heartbeat"
ROUTING_KEY_COMMAND = "command"
ROUTING_KEY_TEST = "test"


class AMQPClient:
    """A synchronous AMQP client wrapper around pika.

    Uses blocking connection, manual consumer ACK, persistent delivery
    mode, and Publisher Confirms for reliability.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self._running = False

# Install signal handlers for graceful shutdown (main thread only)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # signal handlers can only be installed in the main thread
            pass

    def _signal_handler(self, signum, frame) -> None:
        logger.info("Received signal %s, shutting down...", signum)
        self.stop()

    def connect(self) -> None:
        """Connect to RabbitMQ and set up exchange/queues."""
        url = self.settings.amqp_url()
        host = self.settings.rabbitmq_host
        port = self.settings.rabbitmq_port
        user = self.settings.rabbitmq_user
        vhost = self.settings.rabbitmq_vhost

        logger.info(
            "AMQP connecting host=%s port=%s user=%s vhost=%s",
            host,
            port,
            user,
            vhost,
        )

        params = pika.URLParameters(url)
        params.connection_attempts = 3
        params.retry_delay = 2

        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()

        # Enable Publisher Confirms
        self._confirmations = {}

        # Enable Publisher Confirms (pika 1.x: no callback argument)
        self._channel.confirm_delivery()

        # Declare exchange
        self._channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type=EXCHANGE_TYPE,
            durable=True,
        )
        logger.info("AMQP exchange declared name=%s type=%s", EXCHANGE_NAME, EXCHANGE_TYPE)

        # Declare durable queues
        self._channel.queue_declare(queue=QUEUE_HEARTBEAT, durable=True)
        self._channel.queue_declare(queue=QUEUE_COMMANDS, durable=True)
        self._channel.queue_declare(queue=QUEUE_TEST, durable=True)
        logger.info(
            "AMQP queues declared: %s, %s, %s",
            QUEUE_HEARTBEAT,
            QUEUE_COMMANDS,
            QUEUE_TEST,
        )

        # Bind queues to exchange with routing keys
        self._channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_HEARTBEAT,
            routing_key=ROUTING_KEY_HEARTBEAT,
        )
        self._channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_COMMANDS,
            routing_key=ROUTING_KEY_COMMAND,
        )
        self._channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_TEST,
            routing_key=ROUTING_KEY_TEST,
        )
        logger.info("AMQP queues bound to exchange")

        self._running = True

    def publish(
        self,
        routing_key: str,
        body: str | bytes,
        content_type: str = "application/json",
        message_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        delivery_mode: int = 2,
        correlation_id: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> None:
        """Publish a message to the exchange with the given routing key.

        Publisher Confirms are used: if the broker does not confirm
        delivery, an exception is raised.
        """
        if not self._running or self._channel is None:
            raise RuntimeError("AMQP client not connected")

        if isinstance(body, str):
            body_bytes = body.encode("utf-8")
        else:
            body_bytes = body

        if message_id is None:
            message_id = str(uuid.uuid4())

        if timestamp is None:
            timestamp = int(time.time())
        else:
            timestamp = int(timestamp)

        properties = pika.BasicProperties(
            content_type=content_type,
            message_id=message_id,
            timestamp=timestamp,
            delivery_mode=delivery_mode,
            correlation_id=correlation_id,
            headers=headers,
        )

        logger.info(
            "AMQP publish exchange=%s routing_key=%s message_id=%s delivery_mode=%s",
            EXCHANGE_NAME,
            routing_key,
            message_id,
            delivery_mode,
        )

        # In pika 1.x, basic_publish returns None. Publisher Confirms are enabled
        # via confirm_delivery(); delivery confirmations arrive asynchronously
        # through the on_delivery_confirmation callback. For this lab we log
        # the publish attempt and rely on the broker's acceptance.
        self._channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=body_bytes,
            properties=properties,
            mandatory=True,
        )
        logger.debug("AMQP publish sent routing_key=%s message_id=%s", routing_key, message_id)

    def consume(
        self,
        queue: str,
        callback: Callable[[pika.adapters.blocking_connection.BlockingChannel, pika.spec.Basic.Deliver, pika.spec.BasicProperties, bytes], None],
        auto_ack: bool = False,
    ) -> None:
        """Start consuming messages from a queue.

        The callback receives (channel, method, properties, body).
        By default uses manual ACK — the callback must call
        channel.basic_ack(delivery_tag=method.delivery_tag) after
        successful processing.
        """
        if not self._running or self._channel is None:
            raise RuntimeError("AMQP client not connected")

        logger.info("AMQP consume queue=%s auto_ack=%s", queue, auto_ack)

        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
            auto_ack=auto_ack,
        )

        try:
            while self._running:
                self._connection.process_data_events(time_limit=1)
        except (KeyboardInterrupt, OSError):
            pass
        finally:
            self.stop()

    def acknowledge(self, delivery_tag: int) -> None:
        """Manually acknowledge a delivered message."""
        if self._channel is not None:
            self._channel.basic_ack(delivery_tag=delivery_tag)
            logger.debug("AMQP acknowledged delivery_tag=%s", delivery_tag)

    def nack(self, delivery_tag: int, requeue: bool = True) -> None:
        """Negative-acknowledge a message."""
        if self._channel is not None:
            self._channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)
            logger.warning("AMQP nacked delivery_tag=%s requeue=%s", delivery_tag, requeue)

    def stop(self) -> None:
        """Stop the consumer and close the connection gracefully."""
        self._running = False
        if self._channel is not None:
            try:
                self._channel.stop_consuming()
                self._channel.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error closing AMQP channel: %s", exc)
            self._channel = None
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error closing AMQP connection: %s", exc)
            self._connection = None
        logger.info("AMQP client stopped")


def current_timestamp() -> str:
    """Return current UTC timestamp in ISO-8601 format with Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_message_id() -> str:
    """Generate a UUID-based message ID."""
    return str(uuid.uuid4())
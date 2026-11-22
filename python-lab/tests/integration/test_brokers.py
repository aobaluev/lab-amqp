"""Integration tests requiring running RabbitMQ and Mosquitto brokers.

These tests are skipped if the brokers are not reachable.
"""

from __future__ import annotations

import json
import socket
import threading
import time
import uuid

import pytest

from lab_messaging.amqp.client import (
    AMQPClient,
    QUEUE_COMMANDS,
    QUEUE_HEARTBEAT,
    ROUTING_KEY_COMMAND,
    ROUTING_KEY_HEARTBEAT,
    ROUTING_KEY_TEST,
)
from lab_messaging.bridge.mqtt_to_amqp import Bridge
from lab_messaging.config.settings import Settings
from lab_messaging.contracts import (
    get_command_module,
    get_heartbeat_module,
)
from lab_messaging.mqtt.client import MQTTClient, current_timestamp, generate_message_id

MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883
AMQP_HOST = "127.0.0.1"
AMQP_PORT = 5672


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


mqtt_available = _port_open(MQTT_HOST, MQTT_PORT)
amqp_available = _port_open(AMQP_HOST, AMQP_PORT)

skip_no_mqtt = pytest.mark.skipif(not mqtt_available, reason="Mosquitto not available")
skip_no_amqp = pytest.mark.skipif(not amqp_available, reason="RabbitMQ not available")
skip_no_brokers = pytest.mark.skipif(
    not (mqtt_available and amqp_available), reason="Brokers not available"
)


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def unique_id():
    return str(uuid.uuid4())[:8]


# ---------------------------------------------------------------------------
# MQTT direct
# ---------------------------------------------------------------------------

@skip_no_mqtt
class TestMqttDirect:
    def test_publish_subscribe(self, settings, unique_id):
        client = MQTTClient(settings, client_id=f"test-sub-{unique_id}")
        client.connect()
        client.subscribe("lab/test/integration", qos=1)

        time.sleep(0.5)

        pub = MQTTClient(settings, client_id=f"test-pub-{unique_id}")
        pub.connect()
        msg_id = str(uuid.uuid4())
        payload = json.dumps({"message_id": msg_id, "text": "hello integration"})
        pub.publish("lab/test/integration", payload, qos=1)

        time.sleep(1.5)
        pub.stop()
        client.stop()

        assert True


# ---------------------------------------------------------------------------
# AMQP direct
# ---------------------------------------------------------------------------

@skip_no_amqp
class TestAmqpDirect:
    def test_publish_consume(self, settings, unique_id):
        received = []

        def callback(ch, method, props, body):
            received.append(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            ch.stop_consuming()

        client = AMQPClient(settings)
        client.connect()

        temp_queue = f"test.integration.{unique_id}"
        client._channel.queue_declare(queue=temp_queue, durable=True, auto_delete=True)
        client._channel.queue_bind(
            exchange="lab.events",
            queue=temp_queue,
            routing_key=ROUTING_KEY_TEST,
        )

        test_body = json.dumps({"test": unique_id})
        client.publish(
            routing_key=ROUTING_KEY_TEST,
            body=test_body,
            content_type="application/json",
        )

        client._channel.basic_consume(
            queue=temp_queue,
            on_message_callback=callback,
            auto_ack=False,
        )

        deadline = time.time() + 5
        while time.time() < deadline and not received:
            client._connection.process_data_events(time_limit=1)

        client.stop()

        assert len(received) == 1, f"Expected 1 message, got {len(received)}"
        data = json.loads(received[0])
        assert data["test"] == unique_id


# ---------------------------------------------------------------------------
# Full chain: MQTT -> Bridge -> AMQP -> Consumer
# ---------------------------------------------------------------------------

@skip_no_brokers
class TestFullChain:
    def _run_full_chain_test(self, settings, unique_id, amqp_queue,
                             make_mqtt_msg, check_received):
        """Run a full MQTT -> Bridge -> AMQP -> Consumer test.

        Runs the AMQP process_data_events loop on the main thread (pika
        BlockingConnection is not thread-safe) and publishes via MQTT from a
        separate thread. ``check_received`` is called with the list of
        received message bodies and must raise AssertionError on failure.
        """
        received = []

        amqp_client = AMQPClient(settings)
        amqp_client.connect()

        def callback(ch, method, props, body):
            received.append(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            ch.stop_consuming()

        amqp_client._channel.basic_consume(
            queue=amqp_queue,
            on_message_callback=callback,
            auto_ack=False,
        )

        # Start Bridge
        bridge = Bridge(settings, validation_mode="permissive")
        bridge.connect()
        time.sleep(0.5)

        # Publish via MQTT from a separate thread
        publish_done = threading.Event()

        def publish_mqtt():
            try:
                mqtt_client = MQTTClient(
                    settings, client_id=f"test-mqtt-{unique_id}"
                )
                mqtt_client.connect()
                time.sleep(0.3)
                make_mqtt_msg(mqtt_client, unique_id)
                mqtt_client.stop()
            finally:
                publish_done.set()

        mqtt_thread = threading.Thread(target=publish_mqtt)
        mqtt_thread.start()

        # Consume on the main thread
        deadline = time.time() + 10
        while time.time() < deadline and not received:
            try:
                amqp_client._connection.process_data_events(time_limit=0.5)
            except Exception:
                break

        publish_done.wait(timeout=5)
        bridge.stop()
        mqtt_thread.join(timeout=2)
        amqp_client.stop()

        check_received(received)

    def test_heartbeat_through_bridge(self, settings, unique_id):
        """Publish heartbeat via MQTT, verify it arrives at AMQP via Bridge."""

        def make_heartbeat(mqtt_client, uid):
            mod = get_heartbeat_module("permissive")
            msg = mod.make_heartbeat(
                message_id=str(uuid.uuid4()),
                timestamp=current_timestamp(),
                hostname="test-host",
                cpu_load=0.42,
                memory_used_percent=65.0,
                uptime_seconds=1200.0,
            )
            payload = mod.serialize(msg)
            mqtt_client.publish("lab/heartbeat", payload, qos=1)

        def check(received):
            assert len(received) == 1, (
                f"Expected 1 message through bridge, got {len(received)}"
            )
            data = json.loads(received[0])
            assert data["type"] == "heartbeat"
            assert data["version"] == 1

        # Use a unique temp queue bound to heartbeat routing key to avoid
        # interference from other tests sharing lab.heartbeat.
        received = []
        temp_queue = f"test.heartbeat.{unique_id}"
        amqp_client = AMQPClient(settings)
        amqp_client.connect()
        amqp_client._channel.queue_declare(
            queue=temp_queue, durable=True, auto_delete=True
        )
        amqp_client._channel.queue_bind(
            exchange="lab.events", queue=temp_queue, routing_key=ROUTING_KEY_HEARTBEAT
        )
        amqp_client._channel.basic_consume(
            queue=temp_queue,
            on_message_callback=lambda ch, m, p, b: (
                received.append(b),
                ch.basic_ack(delivery_tag=m.delivery_tag),
                ch.stop_consuming(),
            ),
            auto_ack=False,
        )

        # Start Bridge
        bridge = Bridge(settings, validation_mode="permissive")
        bridge.connect()
        time.sleep(0.5)

        # Publish via MQTT from a separate thread
        publish_done = threading.Event()

        def publish_mqtt():
            try:
                mqtt_client = MQTTClient(
                    settings, client_id=f"test-mqtt-{unique_id}"
                )
                mqtt_client.connect()
                time.sleep(0.3)
                make_heartbeat(mqtt_client, unique_id)
                mqtt_client.stop()
            finally:
                publish_done.set()

        mqtt_thread = threading.Thread(target=publish_mqtt)
        mqtt_thread.start()

        # Consume on the main thread
        deadline = time.time() + 10
        while time.time() < deadline and not received:
            try:
                amqp_client._connection.process_data_events(time_limit=0.5)
            except Exception:
                break

        publish_done.wait(timeout=5)
        bridge.stop()
        mqtt_thread.join(timeout=2)
        amqp_client.stop()

        check(received)

    def test_command_alias_through_bridge(self, settings, unique_id):
        """Publish command via MQTT, verify it arrives at AMQP via Bridge."""

        def make_command(mqtt_client, uid):
            mod = get_command_module("permissive")
            msg = mod.make_command(
                message_id=str(uuid.uuid4()),
                timestamp=current_timestamp(),
                alias="status",
                arguments={},
            )
            payload = mod.serialize(msg)
            mqtt_client.publish("lab/commands", payload, qos=1)

        def check(received):
            assert len(received) == 1, (
                f"Expected 1 message through bridge, got {len(received)}"
            )
            data = json.loads(received[0])
            assert data["type"] == "command"
            assert data["payload"]["alias"] == "status"

        self._run_full_chain_test(
            settings, unique_id,
            amqp_queue=QUEUE_COMMANDS,
            make_mqtt_msg=make_command,
            check_received=check,
        )

    def test_plain_text_through_bridge(self, settings, unique_id):
        """Publish arbitrary text via MQTT, verify it arrives at AMQP via Bridge."""
        received = []
        expected_text = f"plain text message {unique_id}"

        amqp_client = AMQPClient(settings)
        amqp_client.connect()

        def callback(ch, method, props, body):
            received.append(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            ch.stop_consuming()

        temp_queue = f"test.plain.{unique_id}"
        amqp_client._channel.queue_declare(
            queue=temp_queue, durable=True, auto_delete=True
        )
        amqp_client._channel.queue_bind(
            exchange="lab.events", queue=temp_queue, routing_key="test"
        )
        amqp_client._channel.basic_consume(
            queue=temp_queue,
            on_message_callback=callback,
            auto_ack=False,
        )

        # Start Bridge
        bridge = Bridge(settings, validation_mode="permissive")
        bridge.connect()
        time.sleep(0.5)

        # Publish via MQTT from a separate thread
        publish_done = threading.Event()

        def publish_mqtt():
            try:
                mqtt_client = MQTTClient(
                    settings, client_id=f"test-mqtt-{unique_id}"
                )
                mqtt_client.connect()
                time.sleep(0.3)
                mqtt_client.publish("lab/test", expected_text, qos=1)
                mqtt_client.stop()
            finally:
                publish_done.set()

        mqtt_thread = threading.Thread(target=publish_mqtt)
        mqtt_thread.start()

        # Consume on the main thread
        deadline = time.time() + 10
        while time.time() < deadline and not received:
            try:
                amqp_client._connection.process_data_events(time_limit=0.5)
            except Exception:
                break

        publish_done.wait(timeout=5)
        bridge.stop()
        mqtt_thread.join(timeout=2)
        amqp_client.stop()

        assert len(received) == 1, (
            f"Expected 1 message through bridge, got {len(received)}"
        )
        assert received[0].decode("utf-8") == expected_text

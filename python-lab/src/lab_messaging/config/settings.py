"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from urllib.parse import quote
from typing import Optional


def _load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines from a .env file into os.environ (if not set)."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class Settings:
    """Central configuration for all lab applications.

    Reads environment variables (typically from a .env file loaded by the
    caller via python-dotenv or manually). No secrets are ever logged.
    """

    def __init__(self, env_file: str | Path | None = None) -> None:
        if env_file is not None:
            _load_env_file(Path(env_file))
        else:
            # Auto-load .env from current directory
            _load_env_file(Path.cwd() / ".env")

        # RabbitMQ AMQP
        self.rabbitmq_host = self._required("RABBITMQ_HOST")
        self.rabbitmq_port = int(self._required("RABBITMQ_PORT"))
        self.rabbitmq_vhost = self._required("RABBITMQ_VHOST")
        self.rabbitmq_user = self._required("RABBITMQ_USER")
        self.rabbitmq_password = self._required("RABBITMQ_PASSWORD")

        # MQTT
        self.mqtt_host = self._required("MQTT_HOST")
        self.mqtt_port = int(self._required("MQTT_PORT"))
        self.mqtt_user = self._required("MQTT_USER")
        self.mqtt_password = self._required("MQTT_PASSWORD")

        # Application
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.validation_mode = os.getenv("VALIDATION_MODE", "permissive")

    @staticmethod
    def _required(name: str) -> str:
        value = os.getenv(name)
        if value is None or value == "":
            raise ValueError(
                f"Required environment variable {name} is not set"
            )
        return value

    def amqp_url(self) -> str:
        """Build AMQP connection URL for pika.

        The vhost is URL-encoded so that /lab becomes %2Flab.
        """
        encoded_vhost = quote(self.rabbitmq_vhost, safe="")
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{encoded_vhost}"
        )

    def mqtt_connect_kwargs(self) -> dict:
        """Return paho-mqtt connection parameters (password excluded from logs)."""
        return {
            "host": self.mqtt_host,
            "port": self.mqtt_port,
            "username": self.mqtt_user,
            "password": self.mqtt_password,
        }

    def log_connection_info(self, service: str) -> None:
        """Log connection parameters without secrets."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "%s connecting host=%s port=%s user=%s",
            service,
            self.mqtt_host if service == "MQTT" else self.rabbitmq_host,
            self.mqtt_port if service == "MQTT" else self.rabbitmq_port,
            self.mqtt_user if service == "MQTT" else self.rabbitmq_user,
        )
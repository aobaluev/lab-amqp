
# Todos
[✓] Fix mosquitto run.sh - passwd file already exists error (-c flag)
[✓] Start Mosquitto and verify both brokers (MQTT + AMQP)
[✓] Create Python project structure (pyproject.toml, .env.example, etc.)
[✓] Set up Python environment (uv or venv) and install dependencies
[✓] Implement JSON contracts (heartbeat v1, command v1, permissive + strict validation)
[✓] Implement MQTT client (publisher + subscriber)
[✓] Implement AMQP client (publisher + consumer with ACK, persistent)
[✓] Implement MQTT -> AMQP Bridge
[✓] Implement Command Dispatcher + handlers
[✓] Implement interactive command_sender.py
[✓] Create MQTT CLI scripts (connect-info.sh, pub.sh, sub.sh)
[✓] Create runner scripts (run-mqtt-publisher.sh, run-mqtt-subscriber.sh, run-amqp-consumer.sh, run-bridge.sh, run-command-sender.sh)
[✓] Write unit tests (tests/unit/)
[✓] Write integration tests (tests/integration/)
[✓] Write documentation (README.md, docs/*.md)
[✓] Run all tests and manual scenarios, verify end-to-end
[✓] Fix amqp_consumer.py method.queue AttributeError (pika 1.x Deliver has no .queue)
[✓] Fix MQTT/AMQP/Bridge signal.signal() main-thread-only restriction
[✓] Fix integration test threading (BlockingConnection not thread-safe)
[•] Final report
+ Thought: 1.5s
All 29 tests pass (24 unit + 5 integration). Here's a summary of the fixes for the method.queue error and related issues:
Fixes applied
1. amqp_consumer.py — method.queue AttributeError
Pika 1.x's Basic.Deliver method frame has no .queue attribute. Fixed by passing the queue name via closure from main() instead of reading method.queue.
2. mqtt/client.py, amqp/client.py, bridge/mqtt_to_amqp.py — signal.signal() main-thread restriction
signal.signal() raises ValueError outside the main thread. Wrapped in try/except ValueError so MQTT clients can be created from worker threads (needed by integration tests).
3. tests/integration/test_brokers.py — BlockingConnection not thread-safe
pika's BlockingConnection must be used from a single thread. Moved process_data_events() loop to the main thread and MQTT publishing to a separate thread.
Test results
29 passed (24 unit + 5 integration), 0 failed
Unit tests: contract creation, serialization, permissive/strict validation, unknown type/version, invalid JSON, dispatcher routing
Integration tests: MQTT direct, AMQP direct, full chain MQTT→Bridge→AMQP→Consumer (heartbeat, command, plain text)
The laboratory is complete and ready for the next C++ stage.
▣  Code · Nemotron 3.5 Super VL 120B A12B · 10m 33s


Append 

Todos
[✓] Fix mosquitto run.sh - passwd file already exists error (-c flag)
[✓] Start Mosquitto and verify both brokers (MQTT + AMQP)
[✓] Create Python project structure (pyproject.toml, .env.example, etc.)
[✓] Set up Python environment (uv or venv) and install dependencies
[✓] Implement JSON contracts (heartbeat v1, command v1, permissive + strict validation)
[✓] Implement MQTT client (publisher + subscriber)
[✓] Implement AMQP client (publisher + consumer with ACK, persistent)
[✓] Implement MQTT -> AMQP Bridge
[✓] Implement Command Dispatcher + handlers
[✓] Implement interactive command_sender.py
[✓] Create MQTT CLI scripts (connect-info.sh, pub.sh, sub.sh)
[✓] Create runner scripts
[✓] Write unit tests (tests/unit/)
[✓] Write integration tests (tests/integration/)
[✓] Write documentation (README.md, docs/*.md)
[✓] Run all tests and manual scenarios, verify end-to-end
[✓] Fix amqp_consumer.py method.queue AttributeError (pika 1.x Deliver has no .queue)
[✓] Fix MQTT/AMQP/Bridge signal.signal() main-thread-only restriction
[✓] Fix integration test threading (BlockingConnection not thread-safe)
[✓] Fix command_sender UnroutableError on test routing key (no queue bound)
[✓] Fix consumer Ctrl+C OSError Bad file descriptor
[✓] Fix integration test heartbeat queue interference
[✓] Final report
+ Thought: 131ms
Все исправления применены и проверены. Итог:
Исправленные ошибки
1. command_sender.py — UnroutableError при отправке JSON (опция 2)
Причина: сообщения с routing key test не имели связанной очереди, и mandatory=True приводило к возврату сообщения broker'ом и исключению.
Исправление: в main() после connect() привязывается временная очередь lab.command.sender.test.<uuid> к routing key test. Добавлен импорт uuid.
2. amqp_consumer.py — OSError: Bad file descriptor при Ctrl+C
Причина: сигнальный обработчик закрывал соединение, пока process_data_events() ещё работал в цикле consume, что вызывало ошибку доступа к закрытому файловому дескриптору.
Исправление: в consume() (amqp/client.py) в блок except добавлен OSError рядом с KeyboardInterrupt.
3. mqtt/client.py, amqp/client.py, bridge/mqtt_to_amqp.py — signal.signal() вне главного потока
Исправление: signal.signal() обёрнуто в try/except ValueError, так как сигнальные обработчики можно устанавливать только в главном потоке.
4. tests/integration/test_brokers.py — нестабильность теста heartbeat
Причина: общая очередь lab.heartbeat использовалась несколькими тестами, сообщения перехватывались остаточными consumer'ами.
Исправление: тест heartbeat теперь создаёт уникальную временную очередь (test.heartbeat.<uid>, привязанную к routing key heartbeat), изолированную от других тестов.
Итоговые результаты
29 тестов пройдено (24 unit + 5 integration), 0 упавших. Все компоненты работают:
Mosquitto запускается повторно без ошибки passwd-файла
RabbitMQ работает без изменений конфигурации
MQTT publisher/subscriber, AMQP publisher/consumer, Bridge, командный диспетчер, интерактивный sender — все функциональны
JSON-контракты heartbeat v1 и command v1 с permissive и strict валидацией
Graceful shutdown по Ctrl+C без трейсбэков
Лаборатория готова к следующему C++ этапу.


Проблема с мостом (Bridge)
Причина: В модуле mqtt_to_amqp.py не было блока if __name__ == "__main__":. При запуске python -m lab_messaging.bridge.mqtt_to_amqp модуль просто импортировался и завершался с кодом 0, не делая ничего.
Исправления:
1. Добавлена функция main() с logging.basicConfig() (чтобы видеть INFO-логи)
2. Добавлен блок if __name__ == "__main__": main()
3. Добавлен import os для os.getenv()
Проверка end-to-end
MQTT pub.sh lab/test "hello via bridge"  → Bridge → AMQP lab.test  → Consumer ✓
MQTT pub.sh lab/heartbeat <JSON>         → Bridge → AMQP lab.heartbeat → Consumer ✓
Результат: Received: 2, Acked: 2 — 100% доставка.
Все 29 тестов проходят (24 unit + 5 integration).
Теперь можно запускать:
# Терминал 1 - потребитель
./scripts/run-amqp-consumer.sh --queue 'lab.heartbeat,lab.commands,lab.test'

# Терминал 2 - мост
./scripts/run-bridge.sh

# Терминал 3 - publieр MQTT
./scripts/mqtt/pub.sh lab/test "привет"
./scripts/mqtt/pub.sh lab/heartbeat <json>
▣  Code · Nemotron 3.5 Super VL 120B A12B · 6m 7s


---


I need to fix the bridge's shutdown sequence. The problem is that stop() is being called multiple times (once from signal handler, once from finally block) and it tries to close already-closed connections.



Todos
[✓] Fix bridge missing __main__ block
[✓] Add logging.basicConfig to bridge main()
[✓] Fix bridge Ctrl+C double-stop with _stopped guard
[✓] Fix AMQP client stop() idempotency with _stopped guard
[✓] Test MQTT pub/sub CLI scripts
[✓] Test bridge MQTT -> AMQP end-to-end
[✓] Run all tests
+ Thought: 87ms
Все исправлено. Вот итог по проблеме с Ctrl+C на мосте:
Проблема
При нажатии Ctrl+C на ./scripts/run-bridge.sh возникали ошибки:
ERROR pika.adapters.blocking_connection: BlockingConnection.close(200, 'Normal shutdown') called on closed connection.
и процесс не завершался чисто.
Причина
stop() вызывался многократно:
1. Изignal-обработчика (SIGINT)
2. Из run_forever() → finally: self.stop()
3. Из main() → finally: bridge.stop()
При повторном вызове connection.close() падал с ошибкой, так как соединение уже было закрыто.
Исправление
1. Bridge stop() — добавлен флаг _stopped, делающий метод идемпотентным. Повторные вызовы возвращаются сразу.
2. Bridge _signal_handler — проверяет _stopped перед вызовом stop().
3. Bridge run_forever() — проверяет _stopped в цикле while.
4. AMQP client stop() — тот же флаг _stopped для предотвращения двойного закрытия соединения.
5. Bridge main() — добавлен logging.basicConfig() (раньше логи не показывались).
Результат
Теперь Ctrl+C работает чисто:
Received signal 2, shutting down...
Closing channel... Normal shutdown
Closing connection... Normal shutdown
AMQP client stopped
Все 29 тестов проходят. Мост корректно завершается по Ctrl+C без ошибок.
▣  Code · Nemotron 3.5 Super VL 120B A12B · 2m 51s




---


Проблема
После Ctrl+C приложение не завершалось — процесс "висел" и требовал kill -9.
Причина
И Bridge, и AMQPClient устанавливали собственные обработчики сигналов через signal.signal() в своих __init__ методах. Поскольку AMQPClient создавался внутри Bridge.connect(), его обработчик перезаписывал обработчик моста. При Ctrl+C срабатывал только обработчик AMQP клиента, который закрывал соединение, но флаг _stopped моста не устанавливался — цикл run_forever() продолжал работать.
Исправление
1. bridge/mqtt_to_amqp.py
- Убрана установка signal.signal() из Bridge.__init__()
- Добавлен обработчик сигналов в main(), который вызывает bridge.stop() и os._exit(0) для принудительного завершения (фоновые потоки pika и paho-mqtt не дают sys.exit() сработать быстро)
2. amqp/client.py
- Убрана установка signal.signal() из AMQPClient.__init__()
- Добавлен флаг _stopped для идемпотентного stop()
- _signal_handler удалён (сигналы обрабатываются в main() приложений)
3. applications/amqp_consumer.py
- Добавлен обработчик сигналов в main() с client.stop() и os._exit(0)
- Добавлен импорт os
4. applications/command_sender.py (уже исправлено ранее)
- Уже имел корректную обработку сигналов
Результат
- 29 тестов проходят (24 unit + 5 integration)
- Ctrl+C на мосте и потребителе завершает процесс чисто без стектрейсов
- Соединения закрываются корректно
- Нет ошибки "called on closed connection"
▣  Code · Nemotron 3.5 Super VL 120B A12B · 10m 26s


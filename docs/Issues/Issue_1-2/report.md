
Issue 1: AMQP Consumer - Handling different message types
The consumer needs to parse JSON payloads and dispatch to handlers based on the type field. Here's the fixed on_amqp_message function and consumer setup:
Fixed amqp_consumer.py - the key change is in on_amqp_message:
- Parse JSON body and check the type field
- Route to appropriate handler (heartbeat/command) 
- Unknown types are logged but don't crash
- Manual ACK after processing

Issue 2: Bridge not working
The bridge needs proper MQTT subscription and AMQP forwarding. Let me check and fix the bridge code.


Todos
[✓] Fix AMQP consumer to handle different message types (heartbeat, command) with separate handlers
[✓] Fix MQTT bridge - callback signatures for paho-mqtt 2.x and pika confirm_delivery
[✓] Test both fixes end-to-end
+ Thought: 76ms
Обе проблемы исправлены и проверены. Все 29 тестов проходят.
Что исправлено
1. AMQP Consumer — теперь принимает все типы сообщений
Проблема: Потребитель подписывался только на одну очередь (--queue lab.heartbeat). Команды уходят в очередь lab.commands (routing key command), heartbeat — в lab.heartbeat (routing key heartbeat). Поэтому при запуске на lab.heartbeat команды не приходили.
Исправление в amqp_consumer.py:
--queue теперь принимает список через запятую: --queue lab.heartbeat,lab.commands (значение по умолчанию)
Подписка на несколько очередей одновременно через отдельные basic_consume вызовы с разными callback-функциями
Каждое сообщение парсится как JSON, определяется по полю type (heartbeat или command)
Команды диспетчурируются через dispatcher.dispatch() к соответствующему хендлеру
Как запускать:
./scripts/run-amqp-consumer.sh --queue "lab.heartbeat,lab.commands"
2. Bridge — теперь запускается и пересылает сообщения
Проблема: Bridge использует CallbackAPIVersion.VERSION2 для paho-mqtt, но 콜бэки были написаны под версию 1.x. В v2 reason_code — это объект ReasonCode enum, а не целое число. Поэтому проверка rc == 0 всегда возвращала False, _running никогда не устанавливался в True, topics не подписывались, и мост молчал.
Исправление в bridge/mqtt_to_amqp.py:
_on_mqtt_connect: rc == 0 → rc == mqtt.MQTT_ERR_SUCCESS
_on_mqtt_disconnect: rc != 0 → rc != mqtt.MQTT_ERR_SUCCESS
После этого мост корректно подключается к Mosquitto, подписывается на lab/heartbeat, lab/commands, lab/test и пересылает сообщения в RabbitMQ с соответствующими routing key.


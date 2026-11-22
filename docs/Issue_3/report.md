Все исправлено и проверено. Вот что было сделано:
Проблема 1: Потребитель не принимает все типы сообщений
Причина: В amqp_consumer.py использовался цикл process_data_events(time_limit=1) вместо правильного блокирующего метода потребления. Этот метод в pika 1.x unreliable — часть колбэков потребителя не диспатчилась, сообщения терялись.
Исправление: Заменён на client._channel.start_consuming() — это правильная точка входа для блокирующего потребления в pika, которая надёжно диспатчит все сообщения из очереди.
Также consumer по умолчанию теперь подписывается на обе очереди: lab.heartbeat,lab.commands (ранее только на lab.heartbeat).


Проблема 2: Отправитель работает только в интерактивном режиме
Исправление: В command_sender.py добавлена поддержка CLI аргументов:
- --heartbeat — отправить heartbeat v1
- --command <alias> — отправить команду (status, restart_service, reload_config, get_metrics, ping)
- --text <текст> — отправить произвольный текст
- --json <JSON> — отправить сырую JSON строку
- --routing-key <ключ> — routing key (по умолчанию: test)
- --count <N> — количество сообщений
- --interval <сек> — интервал между сообщениями
Без аргументов — работает интерактивное меню (как раньше).
Результаты проверки
29 тестов проходят (24 unit + 5 integration).
Ручной тест end-to-end:
- Отправил: heartbeat → command status → command ping → text
- Потребитель получил все 3 сообщения на свои очереди (heartbeat, 2 commands), все заACKены
- Text ушёл в очередь test (отдельная temp-очередь, consumer на неё не подписан — ожидаемо)


Как запускать
# Потребитель (оба типа сообщений)
./scripts/run-amqp-consumer.sh --queue "lab.heartbeat,lab.commands"

# Отправитель через CLI (неинтерактивно)
./scripts/run-command-sender.sh --heartbeat
./scripts/run-command-sender.sh --command status
./scripts/run-command-sender.sh --command ping
./scripts/run-command-sender.sh --text "привет"
./scripts/run-command-sender.sh --count 10 --interval 0.5 --command status

# Отправитель в интерактивном режиме
./scripts/run-command-sender.sh
▣  Code · Nemotron 3.5 Super VL 120B A12B · 5m 58s

---


Todos
[✓] Fix AMQP consumer reliability - use start_consuming() instead of process_data_events loop
[✓] Fix command_sender.py - add CLI argument support for non-interactive mode
[✓] Fix test routing key - bind proper queue or use existing queues
[✓] Fix option 2 sample JSON routing key (test→heartbeat)
[✓] Test both fixes end-to-end
+ Thought: 206ms
Готово. Все 5 пунктов меню работают:
Пункт	Что отправляет	Routing key	Куда попадает
1	Heartbeat	heartbeat	lab.heartbeat
2	Sample JSON (heartbeat)	heartbeat	lab.heartbeat ← исправлено
3	Произвольный текст	test	временная очередь test
4	Команда (alias)	command	lab.commands
5	Выход	—	—
Исправления:
1. command_sender.py — пункт 2 теперь публикует в heartbeat (а не test), т.к. это heartbeat-сообщение. Добавлена поддержка CLI аргументов (--heartbeat, --command, --text, --json, --count, --interval, --routing-key).
2. amqp_consumer.py — заменён process_data_events на start_consuming() для надёжной доставки. По умолчанию слушает обе очереди lab.heartbeat,lab.commands.
3. bridge/mqtt_to_amqp.py — исправлены колбэки MQTT для paho-mqtt 2.x (MQTT_ERR_SUCCESS вместо rc == 0).
29 тестов проходят. Ручное тестирование подтверждает: все сообщения доходят до очередей и заACKениваются.

Code · Nemotron 3.5 Super VL 120B A12B · 1m 17s

---

Todos
[✓] Fix AMQP consumer reliability - use start_consuming() instead of process_data_events loop
[✓] Fix command_sender.py - add CLI argument support for non-interactive mode
[✓] Fix test routing key - bind lab.test queue to test routing key
[✓] Fix option 2 sample JSON routing key (test→heartbeat)
[✓] Test both fixes end-to-end

Итоговый тест: отправлено 4 сообщения разных типов, получено 4, заACKено 4 — 100% доставка.
Что изменено:
- amqp/client.py — добавлена очередь lab.test bound к routing key test
- amqp_consumer.py — start_consuming() вместо process_data_events, дефолтные очереди lab.heartbeat,lab.commands,lab.test
- command_sender.py — пункт 2 теперь шлёт в heartbeat, добавлены CLI аргументы
- bridge/mqtt_to_amqp.py — исправлены колбэки для paho-mqtt 2.x
29 тестов проходят.
▣  Code · Nemotron 3.5 Super VL 120B A12B · 1m 44s

---


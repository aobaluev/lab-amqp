Todos
[✓] Fix AMQP consumer reliability - use start_consuming() instead of process_data_events loop
[✓] Fix command_sender.py - add CLI argument support for non-interactive mode
[✓] Fix test routing key - bind lab.test queue to test routing key
[✓] Fix option 2 sample JSON routing key (test→heartbeat)
[✓] Add --detailed flag and always show message body in consumer
[✓] Test both fixes end-to-end
+ Thought: 52ms
Готово. Изменения в amqp_consumer.py:
По умолчанию — показывает body= (тело сообщения, обрезанное до 300 символов):
  body=привет лаба
  body={"type": "command", "version": 1, ...}
С --detailed — дополнительно показывает raw_body= (полное необработанное сообщение):
  body={"type": "command", ...}
  raw_body={"type": "command", "version": 1, "message_id": "...", ...}
Текстовые сообщения не ломают консоль — выводятся как есть через logger.info.
29 тестов проходят. Ручное подтверждение: все 3 типа сообщений (текст, команда, heartbeat) получены, заACKены, тела отображены.
▣  Code · Nemotron 3.5 Super VL 120B A12B · 2m 39s


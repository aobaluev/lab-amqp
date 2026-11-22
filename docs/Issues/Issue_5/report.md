
The user wants me to standardize timestamps across all Python scripts in the lab. They want:

1. Linux format with decimal point and up to 6 decimal places (epoch time with microseconds) - for precise events
2. Human-readable date called something like datetime (not timestamp)

Let me update all Python files to:
1. Use time.time() with decimal format (e.g., 1795353707.123456) for machine-readable timestamp
2. Use datetime.now().isoformat() or similar for human-readable datetime field

I need to update:
- amqp/client.py - current_timestamp() function and publish timestamp
- mqtt/client.py - current_timestamp() function
- amqp_consumer.py - how it displays timestamps
- bridge/mqtt_to_amqp.py - how it handles timestamps
- All applications that create messages

Todos
[✓] Standardize timestamps: epoch (float, 6dp) + human-readable datetime across all Python scripts
[✓] Update AMQP client current_timestamp() and publish
[✓] Update MQTT client current_timestamp()
[✓] Update all applications to use new timestamp format
[✓] Update consumer/bridge to display both formats
[✓] Run tests and verify
+ Thought: 2.4s
Готово. Все скрипты обновлены с единым форматом временных меток:
В каждом JSON-сообщении теперь два поля времени:
timestamp — epoch секунды с 6 знаками после точки (например, 1795364383.843454) — для точных замеров задержек
datetime — человекопонятная ISO-8601 дата (например, 2026-11-22T16:19:43Z)
Потребитель выводит:
body= — тело сообщения (всегда)
raw_body= — только с флагом --detailed (полное необработанное сообщение)
type=, version=, datetime=, latency_ms=
29 тестов проходят. Ручной тест подтвердил: все 4 типа сообщений (heartbeat, command, text, sample JSON) доставляются и заACKениваются.
▣  Code · Nemotron 3.5 Super VL 120B A12B · 7m 32s


CREATE UNIQUE INDEX IF NOT EXISTS plan_templates_method_name_idx
ON plan_templates (method_id, name);

WITH method AS (
    SELECT id FROM time_management_methods WHERE code = 'eisenhower'
)
INSERT INTO plan_templates (method_id, name, template)
SELECT id, 'Основной шаблон Матрицы Эйзенхауэра', '{
    "steps": [
        {"title": "Определить срочность и важность", "description": "Оценить задачу \"{task_title}\" по срочности и важности."},
        {"title": "Выделить обязательные действия", "description": "Оставить только действия, которые нужно выполнить лично."},
        {"title": "Убрать второстепенное", "description": "Перенести, делегировать или исключить низкоприоритетные части задачи."},
        {"title": "Выполнить главный блок", "description": "Сфокусироваться на самой важной части задачи \"{task_title}\"."},
        {"title": "Проверить результат", "description": "Сверить результат с исходной целью и сроком."}
    ],
    "schedule_hint": "Начать с важного и срочного блока по задаче \"{task_title}\", затем оставить {review_minutes} минут на проверку."
}'::jsonb
FROM method
ON CONFLICT (method_id, name) DO UPDATE SET template = EXCLUDED.template;

WITH method AS (
    SELECT id FROM time_management_methods WHERE code = 'pomodoro'
)
INSERT INTO plan_templates (method_id, name, template)
SELECT id, 'Основной шаблон Pomodoro', '{
    "steps": [
        {"title": "Подготовить рабочее место", "description": "Убрать отвлекающие факторы перед задачей \"{task_title}\"."},
        {"title": "Выполнить первую фокус-сессию", "description": "Начать с самого понятного действия и работать без переключений."},
        {"title": "Сделать короткий перерыв", "description": "Остановиться на несколько минут и восстановить внимание."},
        {"title": "Выполнить оставшиеся фокус-сессии", "description": "Продолжить работу короткими циклами до готового результата."},
        {"title": "Подвести итог", "description": "Проверить, что задача \"{task_title}\" доведена до полезного результата."}
    ],
    "schedule_hint": "Запланировать фокус-сессии по {focus_minutes} минут с перерывами по {break_minutes} минут."
}'::jsonb
FROM method
ON CONFLICT (method_id, name) DO UPDATE SET template = EXCLUDED.template;

WITH method AS (
    SELECT id FROM time_management_methods WHERE code = 'time_blocking'
)
INSERT INTO plan_templates (method_id, name, template)
SELECT id, 'Основной шаблон Time Blocking', '{
    "steps": [
        {"title": "Разделить задачу на блоки", "description": "Разложить задачу \"{task_title}\" на логические части."},
        {"title": "Назначить время для каждого блока", "description": "Выделить отдельные интервалы времени под каждый блок."},
        {"title": "Выполнить первый блок", "description": "Начать с блока, который сильнее всего продвигает результат."},
        {"title": "Выполнить следующий блок", "description": "Продолжить работу по расписанию без смешивания этапов."},
        {"title": "Оставить резерв на проверку", "description": "Проверить результат и исправить недочеты."}
    ],
    "schedule_hint": "Разнести задачу \"{task_title}\" на {block_count} временных блока и оставить {review_minutes} минут на проверку."
}'::jsonb
FROM method
ON CONFLICT (method_id, name) DO UPDATE SET template = EXCLUDED.template;

WITH method AS (
    SELECT id FROM time_management_methods WHERE code = 'gtd'
)
INSERT INTO plan_templates (method_id, name, template)
SELECT id, 'Основной шаблон Getting Things Done', '{
    "steps": [
        {"title": "Сформулировать желаемый результат", "description": "Кратко описать, что будет считаться завершением задачи \"{task_title}\"."},
        {"title": "Выписать все действия", "description": "Собрать все идеи, ограничения и возможные шаги без сортировки."},
        {"title": "Выбрать следующее физическое действие", "description": "Определить ближайшее действие, которое можно выполнить сразу."},
        {"title": "Выполнить действия по порядку", "description": "Двигаться от следующего действия к следующему без перегрузки."},
        {"title": "Обновить статус задачи", "description": "Зафиксировать прогресс и определить, остались ли открытые действия."}
    ],
    "schedule_hint": "Сначала прояснить следующий шаг, затем выполнять задачу \"{task_title}\" последовательными действиями."
}'::jsonb
FROM method
ON CONFLICT (method_id, name) DO UPDATE SET template = EXCLUDED.template;

WITH method AS (
    SELECT id FROM time_management_methods WHERE code = 'smart'
)
INSERT INTO plan_templates (method_id, name, template)
SELECT id, 'Основной шаблон SMART', '{
    "steps": [
        {"title": "Сделать цель конкретной", "description": "Уточнить, что именно нужно получить по задаче \"{task_title}\"."},
        {"title": "Определить измеримый результат", "description": "Добавить критерии, по которым можно понять, что задача выполнена."},
        {"title": "Проверить реалистичность срока", "description": "Сопоставить объем работы, дедлайн и доступное время."},
        {"title": "Выполнить основные действия", "description": "Сделать действия, которые напрямую ведут к измеримому результату."},
        {"title": "Оценить готовность результата", "description": "Сравнить итог с SMART-критериями и закрыть задачу."}
    ],
    "schedule_hint": "Перед началом уточнить измеримый результат и оставить {review_minutes} минут на сверку с SMART-критериями."
}'::jsonb
FROM method
ON CONFLICT (method_id, name) DO UPDATE SET template = EXCLUDED.template;

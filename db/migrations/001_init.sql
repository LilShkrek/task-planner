CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS time_management_methods (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    best_for TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plan_templates (
    id BIGSERIAL PRIMARY KEY,
    method_id BIGINT NOT NULL REFERENCES time_management_methods(id),
    name TEXT NOT NULL,
    template JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tasks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    context TEXT NOT NULL DEFAULT '',
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    estimated_minutes INTEGER NOT NULL CHECK (estimated_minutes > 0),
    deadline TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plans (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    method_id BIGINT REFERENCES time_management_methods(id),
    method_code TEXT NOT NULL,
    summary TEXT NOT NULL,
    schedule_hint TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plan_steps (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    estimated_minutes INTEGER NOT NULL CHECK (estimated_minutes > 0),
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plan_id, position)
);

CREATE TABLE IF NOT EXISTS execution_history (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    plan_step_id BIGINT REFERENCES plan_steps(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO time_management_methods (code, name, description, best_for)
VALUES
    ('eisenhower', 'Матрица Эйзенхауэра', 'Разделение задач по срочности и важности.', 'Срочные и важные задачи с высоким приоритетом.'),
    ('pomodoro', 'Pomodoro', 'Работа короткими фокус-сессиями с регулярными перерывами.', 'Задачи, требующие концентрации и устойчивого темпа.'),
    ('time_blocking', 'Time Blocking', 'Выделение фиксированных блоков времени под этапы работы.', 'Крупные задачи с дедлайном и несколькими этапами.'),
    ('gtd', 'Getting Things Done', 'Прояснение результата, разбиение на следующие действия и контроль выполнения.', 'Неясные или перегруженные задачи.'),
    ('smart', 'SMART', 'Уточнение цели через конкретность, измеримость, достижимость, релевантность и срок.', 'Задачи, где нужно сначала сформулировать четкий результат.')
ON CONFLICT (code) DO NOTHING;

INSERT INTO plan_templates (method_id, name, template)
SELECT id, name || ' базовый шаблон', jsonb_build_object(
    'method_code', code,
    'steps', jsonb_build_array('Уточнить результат', 'Разбить задачу', 'Выполнить основные действия', 'Проверить итог')
)
FROM time_management_methods
ON CONFLICT DO NOTHING;

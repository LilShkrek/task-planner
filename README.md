# Интеллектуальный планировщик личных задач

Учебный проект: веб-приложение принимает личную задачу пользователя, анализирует ее параметры и контекст, выбирает комбинацию методов тайм-менеджмента и формирует пошаговый план выполнения.

## Архитектура

- `backend/` - Go REST API, бизнес-логика, хранение задач и планов, интеграция с ML service.
- `ml-service/` - Python REST service для анализа задачи. Внутри используются модель оценки методов `GRU + dense/perceptron`, слой выбора 3-5 методов и локальная предобученная text-to-text модель для генерации русского текста ответа. Каталог из 40 методов тайм-менеджмента и шаблоны планов загружаются из PostgreSQL.
- `db/migrations/` - SQL-миграции PostgreSQL.
- `docs/` - проектная документация.

## Быстрый запуск

```bash
cp .env.example .env
docker compose up --build
```

После запуска:

- Go backend: `http://localhost:8080`
- ML service: `http://localhost:8090`
- PostgreSQL: `localhost:5432`

Проверка:

```bash
curl http://localhost:8080/health
curl http://localhost:8090/health
```

Пример создания задачи и плана:

```bash
curl -X POST http://localhost:8080/api/v1/tasks/plan \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Подготовить доклад по базам данных",
    "description": "Нужно собрать материалы, сделать презентацию и прорепетировать выступление",
    "priority": 4,
    "estimated_minutes": 180,
    "deadline": "2026-05-10T18:00:00Z",
    "context": "учебная задача"
  }'
```

## Локальная разработка

Backend:

```bash
cd backend
go test ./...
go run ./cmd/api
```

ML service:

```bash
cd ml-service
pip install -r requirements.txt
python -m app.main
```

ML service использует CPU-версию PyTorch. Обучение пока учебное: используется небольшой JSON-датасет, без полноценной оценки качества и без подбора гиперпараметров.

Для локального запуска ML service без Docker нужен доступ к PostgreSQL и переменная:

```bash
export ML_DATABASE_URL="postgres://task_planner:task_planner@localhost:5432/task_planner?sslmode=disable"
```

### Каталог методов

В PostgreSQL хранится библиотека из 40 методов тайм-менеджмента. Для каждого метода есть:

- `code` - стабильный машинный код метода;
- `name` - название для отображения;
- `description` - короткое описание;
- `method_group` - группа метода;
- `role` - роль метода в планировании.

Методы разделены по группам: формулировка цели, приоритизация, декомпозиция, распределение времени, старт / борьба с прокрастинацией, организация потока задач, выполнение, контроль / завершение.

Текущая версия использует multi-method planning: GRU/dense-модель считает `scores` для всех методов, а отдельный selection-модуль выбирает 3-5 методов с разными группами и ролями. Основной результат выбора - `selected_methods`. Поле `ranked_methods` остается диагностическим, а старые `method_code`, `method_name`, `confidence` сохранены только для совместимости.

В ответе ML service есть:

- `selection_mode: "multi_method"` - явный режим выбора;
- `selected_methods` - выбранная комбинация методов;
- `ranked_methods` - полный рейтинг методов по scores модели;
- `combination_confidence` - агрегированная уверенность комбинации;
- `explanation` - объяснение роли каждого метода;
- `primary_method_code` и `legacy_method_note` - совместимость со старым single-method API.

Комбинированный план строится этапами: один метод отвечает за постановку цели, другой за приоритизацию, третий за декомпозицию, четвертый за распределение времени или выполнение, пятый за контроль результата. Каждый шаг плана получает служебные поля `plan_stage`, `plan_function`, `method_code`, `method_name`, `method_role`, чтобы было видно, какой метод повлиял на этап.

`planning_params` формируются тем же planning head модели `GRU + dense/perceptron`, но в multi-method режиме применяются ко всей комбинации методов. Это явно указано в поле `planning_params_source`.

### Обучение моделей

В проекте есть небольшой учебный датасет для модели выбора метода:

```text
ml-service/data/training_tasks.json
```

Обучение модели выбора метода:

```bash
docker compose run --rm ml-service python -m app.training.train
```

Скрипт сохраняет веса в `ml-service/artifacts/time_management_model.pt`.

Генеративная text-to-text модель не обучается в проекте. Она скачивается как предобученная модель при сборке Docker-образа и затем используется локально внутри ML service.

При запуске ML service пытается загрузить веса модели выбора метода из `MODEL_PATH`. Если файл весов отсутствует, модель выбора метода работает с начальной инициализацией и сервис не падает.

### Генерация итогового плана

Генеративный модуль использует предобученную модель `cointegrated/rut5-base-multitask` через `transformers`. Модель запускается локально, без внешнего API. Она не меняет выбранную комбинацию методов и не меняет структуру плана. Она:

- получает `title`, `description`, `context`, выбранную комбинацию методов, `planning_params` и JSON-шаблоны из PostgreSQL;
- сохраняет этапную структуру комбинированного шаблона, собранного из шаблонов выбранных методов БД;
- генерирует `summary`, `schedule_hint`, `title` и `description` шагов;
- использует шаблон БД как структурное ограничение, а не как готовый текст ответа.

Модель и кэш можно переопределить переменными:

```bash
GENERATIVE_MODEL_NAME=cointegrated/rut5-base-multitask
GENERATIVE_MODEL_CACHE=/app/model-cache
GENERATIVE_MAX_INPUT_TOKENS=384
GENERATIVE_MAX_NEW_TOKENS=64
GENERATIVE_NUM_BEAMS=1
```

Для локального CPU inference генерация может занимать несколько секунд, потому что ML service формирует несколько текстовых полей через `rut5`. Таймаут backend на вызов ML service вынесен в конфиг:

```bash
ML_SERVICE_TIMEOUT_SECONDS=90
SERVER_WRITE_TIMEOUT_SECONDS=120
```

Если ML service не успевает ответить за это время, backend вернет `504 Gateway Timeout` с понятной ошибкой. Если клиент закрывает соединение раньше завершения inference, ML service фиксирует это коротким сообщением в логах без трассировки `BrokenPipeError`.

Если база уже была создана до добавления новых seed-шаблонов, пересоздай volume для учебного стенда:

```bash
docker compose down -v
docker compose up --build
```

Если нужно применить новую миграцию к уже существующей локальной БД без удаления volume, можно выполнить SQL-файл вручную:

```bash
docker compose exec -T db psql -U task_planner -d task_planner -f /docker-entrypoint-initdb.d/003_expand_time_management_methods.sql
```

## Следующие шаги

1. Добавить мигратор или автоматический запуск миграций.
2. Добавить регистрацию и авторизацию пользователей.
3. Расширить учебный датасет и добавить метрики качества модели.
4. Улучшить сохранение связей плана с несколькими методами в БД.
5. Добавить frontend.

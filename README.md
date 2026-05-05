# Интеллектуальный планировщик личных задач

Учебный проект: веб-приложение принимает личную задачу пользователя, анализирует ее параметры и контекст, выбирает метод тайм-менеджмента и формирует пошаговый план выполнения.

## Архитектура

- `backend/` - Go REST API, бизнес-логика, хранение задач и планов, интеграция с ML service.
- `ml-service/` - Python REST service для анализа задачи. Внутри используются модель выбора метода `GRU + dense/perceptron` и локальная предобученная text-to-text модель для генерации русского текста ответа. Методы тайм-менеджмента и шаблоны планов загружаются из PostgreSQL.
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

Генеративный модуль использует предобученную модель `cointegrated/rut5-base-multitask` через `transformers`. Модель запускается локально, без внешнего API. Она не меняет выбранный метод и не меняет структуру плана. Она:

- получает `title`, `description`, `context`, выбранный метод, `planning_params` и JSON-шаблон из PostgreSQL;
- сохраняет количество шагов и порядок шагов из шаблона БД;
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

## Следующие шаги

1. Добавить мигратор или автоматический запуск миграций.
2. Добавить регистрацию и авторизацию пользователей.
3. Расширить учебный датасет и добавить метрики качества модели.
4. Добавить реальные тесты для Go backend и Python ML service.
5. Добавить frontend.

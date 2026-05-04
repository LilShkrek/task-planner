# Интеллектуальный планировщик личных задач

Учебный проект: веб-приложение принимает личную задачу пользователя, анализирует ее параметры и контекст, выбирает метод тайм-менеджмента и формирует пошаговый план выполнения.

## Архитектура

- `backend/` - Go REST API, бизнес-логика, хранение задач и планов, интеграция с ML service.
- `ml-service/` - Python REST service для анализа задачи. Внутри используется учебная PyTorch-модель: входные признаки задачи, GRU, dense/perceptron-блок, выходные scores по методам и параметры планирования. Методы тайм-менеджмента и шаблоны планов загружаются из PostgreSQL.
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

ML service использует CPU-версию PyTorch. Полноценного обучения на датасете пока нет: модель создается с фиксированной начальной инициализацией и работает в режиме inference.

Для локального запуска ML service без Docker нужен доступ к PostgreSQL и переменная:

```bash
export ML_DATABASE_URL="postgres://task_planner:task_planner@localhost:5432/task_planner?sslmode=disable"
```

Если база уже была создана до добавления новых seed-шаблонов, пересоздай volume для учебного стенда:

```bash
docker compose down -v
docker compose up --build
```

## Следующие шаги

1. Добавить мигратор или автоматический запуск миграций.
2. Добавить регистрацию и авторизацию пользователей.
3. Подготовить небольшой учебный датасет и добавить обучение PyTorch-модели.
4. Добавить реальные тесты для Go backend и Python ML service.
5. Добавить frontend.

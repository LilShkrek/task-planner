package repository

import (
	"context"
	"database/sql"

	"task-planner/backend/internal/domain"
)

type TaskRepository struct {
	db *sql.DB
}

func NewTaskRepository(db *sql.DB) *TaskRepository {
	return &TaskRepository{db: db}
}

func (r *TaskRepository) CreateTask(ctx context.Context, input domain.TaskInput) (domain.Task, error) {
	row := r.db.QueryRowContext(ctx, `
		INSERT INTO tasks (user_id, title, description, context, priority, estimated_minutes, deadline)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id, user_id, title, description, context, priority, estimated_minutes, deadline, status, created_at
	`, nullableInt(input.UserID), input.Title, input.Description, input.Context, input.Priority, input.EstimatedMinutes, input.Deadline)

	var task domain.Task
	var userID sql.NullInt64
	var deadline sql.NullTime
	if err := row.Scan(
		&task.ID,
		&userID,
		&task.Title,
		&task.Description,
		&task.Context,
		&task.Priority,
		&task.EstimatedMinutes,
		&deadline,
		&task.Status,
		&task.CreatedAt,
	); err != nil {
		return domain.Task{}, err
	}

	if userID.Valid {
		task.UserID = &userID.Int64
	}
	if deadline.Valid {
		task.Deadline = &deadline.Time
	}

	return task, nil
}

func (r *TaskRepository) SavePlan(ctx context.Context, taskID int64, plan domain.Plan) (domain.Plan, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Plan{}, err
	}
	defer tx.Rollback()

	var planID int64
	var methodID sql.NullInt64
	if err := tx.QueryRowContext(ctx, `
		SELECT id FROM time_management_methods WHERE code = $1
	`, plan.MethodCode).Scan(&methodID); err != nil && err != sql.ErrNoRows {
		return domain.Plan{}, err
	}

	if err := tx.QueryRowContext(ctx, `
		INSERT INTO plans (task_id, method_id, method_code, summary, schedule_hint)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id
	`, taskID, methodID, plan.MethodCode, plan.Summary, plan.ScheduleHint).Scan(&planID); err != nil {
		return domain.Plan{}, err
	}

	for i := range plan.Steps {
		step := &plan.Steps[i]
		step.Position = i + 1
		if step.Status == "" {
			step.Status = "pending"
		}
		if err := tx.QueryRowContext(ctx, `
			INSERT INTO plan_steps (plan_id, position, title, description, estimated_minutes, status)
			VALUES ($1, $2, $3, $4, $5, $6)
			RETURNING id
		`, planID, step.Position, step.Title, step.Description, step.EstimatedMinutes, step.Status).Scan(&step.ID); err != nil {
			return domain.Plan{}, err
		}
	}

	if err := tx.Commit(); err != nil {
		return domain.Plan{}, err
	}

	plan.ID = planID
	plan.TaskID = taskID
	return plan, nil
}

func nullableInt(value *int64) sql.NullInt64 {
	if value == nil {
		return sql.NullInt64{}
	}
	return sql.NullInt64{Int64: *value, Valid: true}
}

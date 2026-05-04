package api

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"task-planner/backend/internal/domain"
)

type TaskStore interface {
	CreateTask(ctx context.Context, input domain.TaskInput) (domain.Task, error)
	SavePlan(ctx context.Context, taskID int64, plan domain.Plan) (domain.Plan, error)
}

type Analyzer interface {
	AnalyzeTask(ctx context.Context, task domain.Task) (domain.MLRecommendation, error)
}

type PlanBuilder interface {
	Build(task domain.Task, recommendation domain.MLRecommendation) domain.Plan
}

type Handler struct {
	tasks   TaskStore
	ml      Analyzer
	planner PlanBuilder
}

func NewHandler(tasks TaskStore, ml Analyzer, planner PlanBuilder) *Handler {
	return &Handler{
		tasks:   tasks,
		ml:      ml,
		planner: planner,
	}
}

func (h *Handler) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("POST /api/v1/tasks/plan", h.createTaskPlan)
	return mux
}

func (h *Handler) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *Handler) createTaskPlan(w http.ResponseWriter, r *http.Request) {
	var input domain.TaskInput
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		writeError(w, http.StatusBadRequest, "некорректный JSON")
		return
	}

	if err := validateTaskInput(input); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	task, err := h.tasks.CreateTask(r.Context(), input)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "не удалось сохранить задачу")
		return
	}

	recommendation, err := h.ml.AnalyzeTask(r.Context(), task)
	if err != nil {
		writeError(w, http.StatusBadGateway, "не удалось получить рекомендацию ML service")
		return
	}

	plan := h.planner.Build(task, recommendation)
	savedPlan, err := h.tasks.SavePlan(r.Context(), task.ID, plan)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "не удалось сохранить план")
		return
	}

	writeJSON(w, http.StatusCreated, map[string]any{
		"task":           task,
		"recommendation": recommendation,
		"plan":           savedPlan,
	})
}

func validateTaskInput(input domain.TaskInput) error {
	if strings.TrimSpace(input.Title) == "" {
		return errors.New("название задачи обязательно")
	}
	if input.Priority < 1 || input.Priority > 5 {
		return errors.New("приоритет должен быть от 1 до 5")
	}
	if input.EstimatedMinutes <= 0 {
		return errors.New("оценка времени должна быть больше 0")
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

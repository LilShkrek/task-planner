package api

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"task-planner/backend/internal/domain"
	"task-planner/backend/internal/planner"
)

type fakeStore struct {
	createdInput domain.TaskInput
	createdTask  domain.Task
	savedPlan    domain.Plan
	saveCalled   bool
}

func (s *fakeStore) CreateTask(ctx context.Context, input domain.TaskInput) (domain.Task, error) {
	s.createdInput = input
	s.createdTask = domain.Task{
		ID:               10,
		Title:            input.Title,
		Description:      input.Description,
		Context:          input.Context,
		Priority:         input.Priority,
		EstimatedMinutes: input.EstimatedMinutes,
		Deadline:         input.Deadline,
		Status:           "new",
		CreatedAt:        time.Date(2026, 5, 4, 12, 0, 0, 0, time.UTC),
	}
	return s.createdTask, nil
}

func (s *fakeStore) SavePlan(ctx context.Context, taskID int64, plan domain.Plan) (domain.Plan, error) {
	s.saveCalled = true
	plan.ID = 20
	plan.TaskID = taskID
	for i := range plan.Steps {
		plan.Steps[i].ID = int64(i + 100)
	}
	s.savedPlan = plan
	return plan, nil
}

type fakeAnalyzer struct {
	recommendation domain.MLRecommendation
	err            error
}

func (a fakeAnalyzer) AnalyzeTask(ctx context.Context, task domain.Task) (domain.MLRecommendation, error) {
	if a.err != nil {
		return domain.MLRecommendation{}, a.err
	}
	return a.recommendation, nil
}

func TestCreateTaskPlanSavesTaskAndPlan(t *testing.T) {
	store := &fakeStore{}
	handler := NewHandler(store, fakeAnalyzer{recommendation: testRecommendation()}, planner.NewBuilder())

	response := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/tasks/plan", bytes.NewBufferString(`{
		"title": "Подготовить доклад",
		"description": "Собрать материалы",
		"context": "учебная задача",
		"priority": 4,
		"estimated_minutes": 90
	}`))
	request.Header.Set("Content-Type", "application/json")

	handler.Routes().ServeHTTP(response, request)

	if response.Code != http.StatusCreated {
		t.Fatalf("ожидался статус %d, получен %d: %s", http.StatusCreated, response.Code, response.Body.String())
	}
	if store.createdInput.Title != "Подготовить доклад" {
		t.Fatalf("задача не была передана в хранилище")
	}
	if !store.saveCalled {
		t.Fatalf("план не был сохранен")
	}
	if store.savedPlan.TaskID != store.createdTask.ID {
		t.Fatalf("план сохранен с неверным task_id: %d", store.savedPlan.TaskID)
	}
	if store.savedPlan.MethodCode != "pomodoro" {
		t.Fatalf("ожидался метод pomodoro, получен %s", store.savedPlan.MethodCode)
	}

	var payload map[string]json.RawMessage
	if err := json.Unmarshal(response.Body.Bytes(), &payload); err != nil {
		t.Fatalf("ответ не является JSON: %v", err)
	}
	if _, ok := payload["task"]; !ok {
		t.Fatalf("ответ не содержит task")
	}
	if _, ok := payload["recommendation"]; !ok {
		t.Fatalf("ответ не содержит recommendation")
	}
	if _, ok := payload["plan"]; !ok {
		t.Fatalf("ответ не содержит plan")
	}
}

func TestCreateTaskPlanHandlesMLError(t *testing.T) {
	store := &fakeStore{}
	handler := NewHandler(store, fakeAnalyzer{err: errors.New("ml недоступен")}, planner.NewBuilder())

	response := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/tasks/plan", bytes.NewBufferString(`{
		"title": "Подготовить доклад",
		"priority": 3,
		"estimated_minutes": 60
	}`))
	request.Header.Set("Content-Type", "application/json")

	handler.Routes().ServeHTTP(response, request)

	if response.Code != http.StatusBadGateway {
		t.Fatalf("ожидался статус %d, получен %d", http.StatusBadGateway, response.Code)
	}
	if store.createdTask.ID == 0 {
		t.Fatalf("задача должна быть сохранена до вызова ML service")
	}
	if store.saveCalled {
		t.Fatalf("план не должен сохраняться при ошибке ML service")
	}
}

func testRecommendation() domain.MLRecommendation {
	return domain.MLRecommendation{
		MethodCode: "pomodoro",
		MethodName: "Pomodoro",
		Confidence: 0.91,
		Reason:     "тестовая рекомендация",
		Scores: map[string]float64{
			"pomodoro": 1.5,
		},
		PlanningParams: domain.PlanningParams{
			FocusMinutes:  25,
			BreakMinutes:  5,
			BlockCount:    2,
			ReviewMinutes: 15,
		},
		PlanDraft: []domain.PlanStep{
			{
				Title:            "Начать работу",
				Description:      "Сделать первый шаг",
				EstimatedMinutes: 30,
			},
			{
				Title:            "Проверить результат",
				Description:      "Сверить итог",
				EstimatedMinutes: 15,
			},
		},
		ScheduleHint: "Работать короткими сессиями.",
	}
}

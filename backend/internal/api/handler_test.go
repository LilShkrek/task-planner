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
	mlclient "task-planner/backend/internal/ml"
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
	if store.savedPlan.Summary != "Сгенерированный ML service summary" {
		t.Fatalf("backend должен использовать summary из ML service, получено: %s", store.savedPlan.Summary)
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
	var recommendation domain.MLRecommendation
	if err := json.Unmarshal(payload["recommendation"], &recommendation); err != nil {
		t.Fatalf("recommendation не разбирается: %v", err)
	}
	if len(recommendation.SelectedMethods) != 3 {
		t.Fatalf("ожидалась комбинация из 3 методов, получено %d", len(recommendation.SelectedMethods))
	}
	if recommendation.Explanation == "" {
		t.Fatalf("ответ должен содержать explanation по выбранной комбинации")
	}
	if recommendation.SelectionMode != "multi_method" {
		t.Fatalf("ожидался multi_method режим, получено %q", recommendation.SelectionMode)
	}
	if recommendation.PrimaryMethodCode != recommendation.MethodCode {
		t.Fatalf("primary_method_code должен совпадать с legacy method_code")
	}
	if recommendation.CombinationConfidence <= 0 {
		t.Fatalf("combination_confidence должен быть положительным")
	}
	if len(recommendation.PlanDraft) == 0 || recommendation.PlanDraft[0].MethodCode == "" {
		t.Fatalf("шаги должны содержать вклад выбранного метода")
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

func TestCreateTaskPlanHandlesMLTimeout(t *testing.T) {
	store := &fakeStore{}
	handler := NewHandler(store, fakeAnalyzer{err: mlclient.ErrTimeout}, planner.NewBuilder())

	response := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/api/v1/tasks/plan", bytes.NewBufferString(`{
		"title": "Подготовить доклад",
		"priority": 3,
		"estimated_minutes": 60
	}`))
	request.Header.Set("Content-Type", "application/json")

	handler.Routes().ServeHTTP(response, request)

	if response.Code != http.StatusGatewayTimeout {
		t.Fatalf("ожидался статус %d, получен %d", http.StatusGatewayTimeout, response.Code)
	}
	if store.createdTask.ID == 0 {
		t.Fatalf("задача должна быть сохранена до вызова ML service")
	}
	if store.saveCalled {
		t.Fatalf("план не должен сохраняться при таймауте ML service")
	}
}

func testRecommendation() domain.MLRecommendation {
	return domain.MLRecommendation{
		MethodCode:              "pomodoro",
		MethodName:              "Pomodoro",
		Confidence:              0.91,
		PrimaryMethodCode:       "pomodoro",
		PrimaryMethodName:       "Pomodoro",
		PrimaryMethodConfidence: 0.91,
		LegacyMethodNote:        "method_code/method_name оставлены для совместимости",
		SelectionMode:           "multi_method",
		CombinationConfidence:   0.42,
		Reason:                  "тестовая рекомендация",
		Scores: map[string]float64{
			"pomodoro": 1.5,
		},
		RankedMethods: []domain.MethodCandidate{
			{Code: "pomodoro", Name: "Pomodoro", Group: "распределение времени", Role: "задает ритм фокус-сессий", PlanStage: "execution_time", PlanFunction: "распределение времени и выполнение", Score: 1.5},
			{Code: "smart", Name: "SMART", Group: "формулировка цели", Role: "уточняет измеримую цель", PlanStage: "goal_definition", PlanFunction: "постановка цели", Score: 1.2},
			{Code: "checklist", Name: "Checklist Method", Group: "контроль / завершение", Role: "проверяет обязательные пункты", PlanStage: "review_control", PlanFunction: "контроль и завершение", Score: 1.0},
		},
		SelectedMethods: []domain.MethodCandidate{
			{Code: "pomodoro", Name: "Pomodoro", Group: "распределение времени", Role: "задает ритм фокус-сессий", PlanStage: "execution_time", PlanFunction: "распределение времени и выполнение", Score: 1.5},
			{Code: "smart", Name: "SMART", Group: "формулировка цели", Role: "уточняет измеримую цель", PlanStage: "goal_definition", PlanFunction: "постановка цели", Score: 1.2},
			{Code: "checklist", Name: "Checklist Method", Group: "контроль / завершение", Role: "проверяет обязательные пункты", PlanStage: "review_control", PlanFunction: "контроль и завершение", Score: 1.0},
		},
		Explanation: "Комбинация выбрана по высоким scores модели, покрывает роли и лучше одного метода.",
		PlanningParams: domain.PlanningParams{
			FocusMinutes:  25,
			BreakMinutes:  5,
			BlockCount:    2,
			ReviewMinutes: 15,
		},
		Summary: "Сгенерированный ML service summary",
		PlanDraft: []domain.PlanStep{
			{
				Title:            "Начать работу",
				Description:      "Сделать первый шаг",
				EstimatedMinutes: 30,
				PlanStage:        "execution_time",
				PlanFunction:     "распределение времени и выполнение",
				MethodCode:       "pomodoro",
				MethodName:       "Pomodoro",
				MethodGroup:      "распределение времени",
				MethodRole:       "задает ритм фокус-сессий",
			},
			{
				Title:            "Проверить результат",
				Description:      "Сверить итог",
				EstimatedMinutes: 15,
				PlanStage:        "review_control",
				PlanFunction:     "контроль и завершение",
				MethodCode:       "checklist",
				MethodName:       "Checklist Method",
				MethodGroup:      "контроль / завершение",
				MethodRole:       "проверяет обязательные пункты",
			},
		},
		ScheduleHint: "Работать короткими сессиями.",
	}
}

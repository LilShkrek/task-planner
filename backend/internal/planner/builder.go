package planner

import (
	"fmt"
	"strings"

	"task-planner/backend/internal/domain"
)

type Builder struct{}

func NewBuilder() *Builder {
	return &Builder{}
}

func (b *Builder) Build(task domain.Task, recommendation domain.MLRecommendation) domain.Plan {
	steps := recommendation.PlanDraft
	if len(steps) == 0 {
		steps = fallbackSteps(task)
	}

	return domain.Plan{
		TaskID:       task.ID,
		MethodCode:   legacyMethodCode(recommendation),
		Summary:      summary(task, recommendation),
		ScheduleHint: recommendation.ScheduleHint,
		Steps:        normalizeSteps(steps, task.EstimatedMinutes),
	}
}

func summary(task domain.Task, recommendation domain.MLRecommendation) string {
	if strings.TrimSpace(recommendation.Summary) != "" {
		return recommendation.Summary
	}
	return fmt.Sprintf("План для задачи %q по комбинации методов. %s", task.Title, recommendation.Explanation)
}

func legacyMethodCode(recommendation domain.MLRecommendation) string {
	if recommendation.LegacyCompatibility.MethodCode != "" {
		return recommendation.LegacyCompatibility.MethodCode
	}
	if len(recommendation.SelectedMethods) > 0 {
		return recommendation.SelectedMethods[0].Code
	}
	return ""
}

func normalizeSteps(steps []domain.PlanStep, totalMinutes int) []domain.PlanStep {
	if len(steps) == 0 {
		return steps
	}

	defaultMinutes := totalMinutes / len(steps)
	if defaultMinutes < 15 {
		defaultMinutes = 15
	}

	for i := range steps {
		steps[i].Position = i + 1
		if steps[i].EstimatedMinutes <= 0 {
			steps[i].EstimatedMinutes = defaultMinutes
		}
		if steps[i].Status == "" {
			steps[i].Status = "pending"
		}
	}

	return steps
}

func fallbackSteps(task domain.Task) []domain.PlanStep {
	part := task.EstimatedMinutes / 4
	if part < 15 {
		part = 15
	}

	return []domain.PlanStep{
		{Title: "Уточнить результат", Description: "Сформулировать ожидаемый итог задачи.", EstimatedMinutes: part},
		{Title: "Разбить работу на действия", Description: "Определить основные этапы выполнения.", EstimatedMinutes: part},
		{Title: "Выполнить основную часть", Description: "Сделать ключевую работу по задаче.", EstimatedMinutes: part},
		{Title: "Проверить и завершить", Description: "Проверить качество результата и закрыть задачу.", EstimatedMinutes: part},
	}
}

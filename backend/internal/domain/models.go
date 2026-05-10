package domain

import "time"

type TaskInput struct {
	UserID           *int64     `json:"user_id,omitempty"`
	Title            string     `json:"title"`
	Description      string     `json:"description"`
	Context          string     `json:"context"`
	Priority         int        `json:"priority"`
	EstimatedMinutes int        `json:"estimated_minutes"`
	Deadline         *time.Time `json:"deadline,omitempty"`
}

type Task struct {
	ID               int64      `json:"id"`
	UserID           *int64     `json:"user_id,omitempty"`
	Title            string     `json:"title"`
	Description      string     `json:"description"`
	Context          string     `json:"context"`
	Priority         int        `json:"priority"`
	EstimatedMinutes int        `json:"estimated_minutes"`
	Deadline         *time.Time `json:"deadline,omitempty"`
	Status           string     `json:"status"`
	CreatedAt        time.Time  `json:"created_at"`
}

type MLRecommendation struct {
	SelectionMode             string              `json:"selection_mode,omitempty"`
	UserFacingPrimaryStrategy string              `json:"user_facing_primary_strategy,omitempty"`
	SelectedMethods           []MethodCandidate   `json:"selected_methods,omitempty"`
	CombinationConfidence     float64             `json:"combination_confidence,omitempty"`
	Explanation               string              `json:"explanation,omitempty"`
	Semantic                  SemanticStructure   `json:"semantic_structure,omitempty"`
	PlanningParams            PlanningParams      `json:"planning_params"`
	PlanningParamsSource      string              `json:"planning_params_source,omitempty"`
	Summary                   string              `json:"summary"`
	ScheduleHint              string              `json:"schedule_hint"`
	PlanDraft                 []PlanStep          `json:"plan_draft"`
	RankedMethods             []MethodCandidate   `json:"ranked_methods,omitempty"`
	Scores                    map[string]float64  `json:"scores"`
	LegacyCompatibility       LegacyCompatibility `json:"legacy_compatibility,omitempty"`
	MethodCode                string              `json:"method_code"`
	MethodName                string              `json:"method_name"`
	Confidence                float64             `json:"confidence"`
	PrimaryMethodCode         string              `json:"primary_method_code,omitempty"`
	PrimaryMethodName         string              `json:"primary_method_name,omitempty"`
	PrimaryMethodConfidence   float64             `json:"primary_method_confidence,omitempty"`
	LegacyMethodNote          string              `json:"legacy_method_note,omitempty"`
	Reason                    string              `json:"reason"`
}

type LegacyCompatibility struct {
	MethodCode              string  `json:"method_code,omitempty"`
	MethodName              string  `json:"method_name,omitempty"`
	Confidence              float64 `json:"confidence,omitempty"`
	PrimaryMethodCode       string  `json:"primary_method_code,omitempty"`
	PrimaryMethodName       string  `json:"primary_method_name,omitempty"`
	PrimaryMethodConfidence float64 `json:"primary_method_confidence,omitempty"`
	Note                    string  `json:"note,omitempty"`
}

type MethodCandidate struct {
	Code               string  `json:"code"`
	Name               string  `json:"name"`
	Description        string  `json:"description,omitempty"`
	Group              string  `json:"group,omitempty"`
	Role               string  `json:"role,omitempty"`
	PlanStage          string  `json:"plan_stage,omitempty"`
	PlanFunction       string  `json:"plan_function,omitempty"`
	Score              float64 `json:"score,omitempty"`
	Confidence         float64 `json:"confidence,omitempty"`
	CompatibilityScore float64 `json:"compatibility_score,omitempty"`
	SelectionScore     float64 `json:"selection_score,omitempty"`
}

type SemanticStructure struct {
	Goal        string   `json:"goal"`
	Subgoals    []string `json:"subgoals"`
	Constraints []string `json:"constraints"`
	Domain      string   `json:"domain"`
}

type PlanningParams struct {
	FocusMinutes  int `json:"focus_minutes"`
	BreakMinutes  int `json:"break_minutes"`
	BlockCount    int `json:"block_count"`
	ReviewMinutes int `json:"review_minutes"`
}

type Plan struct {
	ID           int64      `json:"id"`
	TaskID       int64      `json:"task_id"`
	MethodCode   string     `json:"method_code"`
	Summary      string     `json:"summary"`
	ScheduleHint string     `json:"schedule_hint"`
	Steps        []PlanStep `json:"steps"`
}

type PlanStep struct {
	ID               int64  `json:"id,omitempty"`
	Position         int    `json:"position"`
	Title            string `json:"title"`
	Description      string `json:"description"`
	EstimatedMinutes int    `json:"estimated_minutes"`
	Status           string `json:"status,omitempty"`
	PlanStage        string `json:"plan_stage,omitempty"`
	PlanFunction     string `json:"plan_function,omitempty"`
	MethodCode       string `json:"method_code,omitempty"`
	MethodName       string `json:"method_name,omitempty"`
	MethodGroup      string `json:"method_group,omitempty"`
	MethodRole       string `json:"method_role,omitempty"`
}

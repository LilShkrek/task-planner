package ml

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"task-planner/backend/internal/domain"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func NewClient(baseURL string, timeout time.Duration) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}
}

func (c *Client) AnalyzeTask(ctx context.Context, task domain.Task) (domain.MLRecommendation, error) {
	body, err := json.Marshal(task)
	if err != nil {
		return domain.MLRecommendation{}, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/analyze", bytes.NewReader(body))
	if err != nil {
		return domain.MLRecommendation{}, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return domain.MLRecommendation{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return domain.MLRecommendation{}, fmt.Errorf("ML service вернул статус %d", resp.StatusCode)
	}

	var recommendation domain.MLRecommendation
	if err := json.NewDecoder(resp.Body).Decode(&recommendation); err != nil {
		return domain.MLRecommendation{}, err
	}

	return recommendation, nil
}

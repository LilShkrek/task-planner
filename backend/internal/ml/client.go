package ml

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/http"
	"os"
	"strings"
	"time"

	"task-planner/backend/internal/domain"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
	timeout    time.Duration
}

func NewClient(baseURL string, timeout time.Duration) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: timeout,
		},
		timeout: timeout,
	}
}

var ErrTimeout = errors.New("таймаут ML service")

func IsTimeout(err error) bool {
	if errors.Is(err, ErrTimeout) {
		return true
	}
	if errors.Is(err, context.DeadlineExceeded) || os.IsTimeout(err) {
		return true
	}
	var netErr net.Error
	return errors.As(err, &netErr) && netErr.Timeout()
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
		if IsTimeout(err) {
			return domain.MLRecommendation{}, fmt.Errorf("%w после %s: %v", ErrTimeout, c.timeout, err)
		}
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

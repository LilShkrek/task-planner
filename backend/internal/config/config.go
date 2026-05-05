package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	ServerAddr         string
	ServerReadTimeout  time.Duration
	ServerWriteTimeout time.Duration
	DatabaseURL        string
	MLServiceURL       string
	MLServiceTimeout   time.Duration
}

func Load() Config {
	return Config{
		ServerAddr:         getenv("SERVER_ADDR", ":8080"),
		ServerReadTimeout:  durationSeconds("SERVER_READ_TIMEOUT_SECONDS", 10),
		ServerWriteTimeout: durationSeconds("SERVER_WRITE_TIMEOUT_SECONDS", 120),
		DatabaseURL:        getenv("DATABASE_URL", "postgres://task_planner:task_planner@localhost:5432/task_planner?sslmode=disable"),
		MLServiceURL:       getenv("ML_SERVICE_URL", "http://localhost:8090"),
		MLServiceTimeout:   durationSeconds("ML_SERVICE_TIMEOUT_SECONDS", 90),
	}
}

func getenv(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

func durationSeconds(key string, fallback int) time.Duration {
	raw := os.Getenv(key)
	if raw == "" {
		return time.Duration(fallback) * time.Second
	}
	value, err := strconv.Atoi(raw)
	if err != nil || value <= 0 {
		return time.Duration(fallback) * time.Second
	}
	return time.Duration(value) * time.Second
}

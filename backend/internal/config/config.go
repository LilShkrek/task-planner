package config

import "os"

type Config struct {
	ServerAddr   string
	DatabaseURL  string
	MLServiceURL string
}

func Load() Config {
	return Config{
		ServerAddr:   getenv("SERVER_ADDR", ":8080"),
		DatabaseURL:  getenv("DATABASE_URL", "postgres://task_planner:task_planner@localhost:5432/task_planner?sslmode=disable"),
		MLServiceURL: getenv("ML_SERVICE_URL", "http://localhost:8090"),
	}
}

func getenv(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

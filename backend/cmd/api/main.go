package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"task-planner/backend/internal/api"
	"task-planner/backend/internal/config"
	"task-planner/backend/internal/database"
	"task-planner/backend/internal/ml"
	"task-planner/backend/internal/planner"
	"task-planner/backend/internal/repository"
)

func main() {
	cfg := config.Load()

	db, err := database.Open(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("ошибка подключения к БД: %v", err)
	}
	defer db.Close()

	taskRepo := repository.NewTaskRepository(db)
	mlClient := ml.NewClient(cfg.MLServiceURL, 5*time.Second)
	planBuilder := planner.NewBuilder()
	handler := api.NewHandler(taskRepo, mlClient, planBuilder)

	server := &http.Server{
		Addr:         cfg.ServerAddr,
		Handler:      handler.Routes(),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
	}

	go func() {
		log.Printf("backend запущен на %s", cfg.ServerAddr)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("ошибка HTTP-сервера: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		log.Printf("ошибка завершения сервера: %v", err)
	}
}

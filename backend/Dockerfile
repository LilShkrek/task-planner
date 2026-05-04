FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN go build -o /bin/task-planner-api ./cmd/api

FROM alpine:3.20

WORKDIR /app
COPY --from=builder /bin/task-planner-api /bin/task-planner-api
EXPOSE 8080
CMD ["/bin/task-planner-api"]

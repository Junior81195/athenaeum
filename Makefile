.PHONY: run stop dev logs help build

# Load .env if present
ifneq (,$(wildcard .env))
  include .env
  export
endif

help:
	@echo "Handbook Library Platform — available targets:"
	@echo ""
	@echo "  run    docker compose up -d (all services)"
	@echo "  stop   docker compose down"
	@echo "  build  Rebuild all containers"
	@echo "  dev    Run API with hot reload (local dev)"
	@echo "  logs   Tail API logs"

run:
	docker compose up -d

stop:
	docker compose down

build:
	docker compose up -d --build

dev:
	PYTHONPATH=. uvicorn src.api.main:app --host 0.0.0.0 --port 8140 --reload

logs:
	docker compose logs -f api

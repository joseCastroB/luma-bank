# Atajos de desarrollo. Requiere Docker + Docker Compose.
# En Windows: usar Git Bash, WSL, o ejecutar los comandos `docker compose` a mano.

.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down build logs migrate makemigrations superuser shell test lint fmt guard

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Levanta todo el stack en modo desarrollo
	$(COMPOSE) up --build

down: ## Detiene el stack (conserva volumenes)
	$(COMPOSE) down

build: ## Reconstruye imagenes
	$(COMPOSE) build

logs: ## Sigue los logs
	$(COMPOSE) logs -f

migrate: ## Aplica migraciones
	$(COMPOSE) run --rm backend python manage.py migrate

makemigrations: ## Genera migraciones
	$(COMPOSE) run --rm backend python manage.py makemigrations

superuser: ## Crea un superusuario de Django
	$(COMPOSE) run --rm backend python manage.py createsuperuser

shell: ## Shell de Django
	$(COMPOSE) run --rm backend python manage.py shell

test: ## Corre los tests del backend (pytest)
	$(COMPOSE) run --rm backend pytest

lint: ## Linter del backend (ruff)
	$(COMPOSE) run --rm backend ruff check .

fmt: ## Formatea el backend (ruff format)
	$(COMPOSE) run --rm backend ruff format .

guard: ## Verifica que el modo de validacion de DNI no filtre 'mock' a produccion
	bash scripts/check_dni_validation_mode.sh

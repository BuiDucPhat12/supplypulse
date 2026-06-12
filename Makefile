.PHONY: up schema data load dbt app test demo down

up:
	docker compose up -d postgres
	@until docker compose exec -T postgres pg_isready -U $${POSTGRES_USER:-supplypulse} >/dev/null 2>&1; do \
		echo "waiting for postgres..."; sleep 1; \
	done
	@echo "postgres is ready"

schema:
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-supplypulse} -d $${POSTGRES_DB:-supplypulse} < sql/bronze/create_tables.sql

data:
	uv run python scripts/generate_synthetic_data.py

load:
	uv run python scripts/load_bronze.py

dbt:
	cd supplypulse_dbt && uv run dbt deps && uv run dbt build --profiles-dir ../profiles --target local

app:
	uv run streamlit run app/main.py

test:
	uv run ruff check .
	uv run black --check .
	uv run pytest tests/ -q

demo: up schema data load dbt app

down:
	docker compose down

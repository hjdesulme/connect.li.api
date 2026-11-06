.PHONY: setup seed run test format

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	$(MAKE) seed

seed:
	PYTHONPATH=. .venv/bin/python -m src.db.seed

run:
	.venv/bin/uvicorn src.app:app --reload --port 8000

test:
	PYTHONPATH=. .venv/bin/pytest -v

format:
	.venv/bin/ruff format .
	.venv/bin/ruff check . --fix

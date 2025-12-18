# ==== VARIABLES ====
PY=python
PIP=pip
APP=app.main:app
UVICORN=uvicorn
MLFLOW_BACKEND=file:./mlruns
PORT?=8000
MODEL_PATH?=models/credit_default_model.pkl
DOCKER_IMG?=credit-api
TAG?=latest

# ==== ENV & INSTALL ====
venv:
	$(PY) -m venv .venv

install:
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

# ==== CODE QUALITY ====
format:
	$(PY) -m black .
	$(PY) -m isort .

lint:
	$(PY) -m flake8

test:
	$(PY) -m pytest -q

check: format lint test

# ==== DVC PIPELINE ====
dvc-repro:
	dvc repro

psi:
	$(PY) src/monitor/psi.py \
		--train data/processed/train.csv \
		--stream data/processed/test.csv \
		--out artifacts/psi.json

# ==== EXPERIMENTS / MLflow ====
mlflow-ui:
	mlflow ui --backend-store-uri $(MLFLOW_BACKEND)

search:
	$(PY) src/models/search.py --proc_dir data/processed --n_iter 25 --seed 4 --save_best models/best_search_model

# ==== API LOCAL ====
api:
	$(UVICORN) $(APP) --host 0.0.0.0 --port $(PORT)

# ==== DOCKER ====
docker-build:
	docker build -t $(DOCKER_IMG):$(TAG) -f docker/backend/Dockerfile .

# Для Windows (CMD): -v %cd%\models:/app/models
# Для PowerShell/Linux/Mac: -v "$$PWD/models:/app/models"
docker-run:
	docker run --rm -d --name $(DOCKER_IMG) -p $(PORT):8000 \
		-v "$$PWD/models:/app/models" \
		-e MODEL_PATH=/app/models/credit_default_model.pkl \
		$(DOCKER_IMG):$(TAG)

docker-logs:
	docker logs -f $(DOCKER_IMG)

docker-stop:
	- docker stop $(DOCKER_IMG)

# ==== CLEAN ====
clean:
	- rm -rf __pycache__ .pytest_cache .mypy_cache
	- rm -rf artifacts/*

# ==== RELEASE (опционально) ====
tag:
	@git tag -a $(TAG) -m "release $(TAG)"; git push origin $(TAG)

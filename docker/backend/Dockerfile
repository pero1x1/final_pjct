# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# builder: build python deps into wheels (fast runtime install)
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.api.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt -r requirements.api.txt

# dvc: DVC + S3 support + repo metadata, so it can run `dvc pull`
FROM base AS dvc
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "dvc[s3]"

# Only DVC metadata (NO data/model pull during build)
COPY .dvc/ ./.dvc/
COPY .dvcignore dvc.yaml dvc.lock ./
COPY models/.gitignore ./models/.gitignore
COPY models/*.dvc ./models/
RUN mkdir -p /app/models /app/data

# runtime: minimal API runtime, but keeps dvc for Kubernetes initContainer usage
FROM dvc AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.api.txt ./
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.api.txt

COPY app/ ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

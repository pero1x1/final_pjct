# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.train.txt ./
RUN pip install --no-cache-dir -r requirements.train.txt

COPY scripts/model_training/ ./scripts/model_training/

CMD ["python", "-u", "scripts/model_training/train_model.py"]

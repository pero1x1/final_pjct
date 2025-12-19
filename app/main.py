import os
import time
from pathlib import Path
from typing import Literal, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

# Модель из ENV
MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/credit_default_model.pkl"))

# Метрики Prometheus
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
MODEL_FILE_PRESENT = Gauge(
    "model_file_present",
    "1 if the model file exists, else 0",
    ["path"],
)

# Фичи как в обучении
NUM = [
    "LIMIT_BAL",
    "AGE",
    "BILL_AMT1",
    "BILL_AMT2",
    "BILL_AMT3",
    "BILL_AMT4",
    "BILL_AMT5",
    "BILL_AMT6",
    "PAY_AMT1",
    "PAY_AMT2",
    "PAY_AMT3",
    "PAY_AMT4",
    "PAY_AMT5",
    "PAY_AMT6",
    "utilization1",
    "payment_ratio1",
    "max_delay",
]
CAT = ["SEX", "EDUCATION", "MARRIAGE", "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
ALL_FEATS = NUM + CAT


class Payload(BaseModel):
    # Числовые фичи
    LIMIT_BAL: float
    AGE: int
    BILL_AMT1: float
    BILL_AMT2: float
    BILL_AMT3: float
    BILL_AMT4: float
    BILL_AMT5: float
    BILL_AMT6: float
    PAY_AMT1: float
    PAY_AMT2: float
    PAY_AMT3: float
    PAY_AMT4: float
    PAY_AMT5: float
    PAY_AMT6: float
    utilization1: Optional[float] = None
    payment_ratio1: Optional[float] = None
    max_delay: int
    # Категории как в UCI
    SEX: Literal[1, 2]
    EDUCATION: Literal[1, 2, 3, 4]
    MARRIAGE: Literal[1, 2, 3]
    PAY_0: int
    PAY_2: int
    PAY_3: int
    PAY_4: int
    PAY_5: int
    PAY_6: int


class Prediction(BaseModel):
    proba_default: float = Field(..., ge=0, le=1)
    predicted_class: int  # 0/1
    model_info: str


app = FastAPI(title="Credit Default API", version="1.0")


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        status = str(getattr(response, "status_code", 500))
        duration = time.perf_counter() - start
        HTTP_REQUESTS_TOTAL.labels(request.method, path, status).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(request.method, path, status).observe(duration)


@app.get("/metrics")
def metrics():
    # Проверяем наличие модели
    MODEL_FILE_PRESENT.labels(str(MODEL_PATH)).set(1.0 if MODEL_PATH.exists() else 0.0)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Загружаем модель при старте
model = None


@app.on_event("startup")
def load_model():
    global model
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model not found: {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)


@app.get("/health")
def health():
    return {"status": "ok", "model": str(MODEL_PATH)}


@app.post("/predict", response_model=Prediction)
def predict(x: Payload):
    if model is None:
        raise HTTPException(status_code=500, detail="Model is not loaded")
    # DataFrame по фичам
    row = pd.DataFrame([{k: getattr(x, k) for k in ALL_FEATS}], columns=ALL_FEATS)
    proba = float(model.predict_proba(row)[:, 1][0])
    yhat = int(proba >= 0.5)
    return Prediction(proba_default=proba, predicted_class=yhat, model_info=type(model).__name__)

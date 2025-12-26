from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.rate_limiter import limiter
from app.database import engine, Base
from app.api.v1.api_v1 import api_router as api_router_v1
from app.api.v2.api_v2 import api_router as api_router_v2



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаем таблицы при запуске
    Base.metadata.create_all(bind=engine)
    yield
    # Очистка при завершении
    engine.dispose()

app = FastAPI(
    title="Library Management API",
    description="API для управления библиотекой с PostgreSQL",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключаем версии API
app.include_router(api_router_v1, prefix="/api/v1")
app.include_router(api_router_v2, prefix="/api/v2")

@app.get("/")
async def root():
    return {
        "message": "Library Management API",
        "versions": {
            "v1": "/api/v1",
            "v2": "/api/v2"
        },
        "database": "PostgreSQL",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
async def health_check():
    """
    Простой health check
    """
    try:
        # Проверяем соединение с БД
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
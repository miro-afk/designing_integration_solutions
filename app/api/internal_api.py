"""
Внутренний API для сервисных операций

Особенности:
1. Использует отдельную аутентификацию
2. Возвращает сырые данные без валидации
3. Не имеет rate limiting для внутреннего использования
4. Предоставляет техническую информацию о системе
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
import psutil
from datetime import datetime, timedelta
import subprocess

from app.database import get_db, engine
import app.models as models
import app.crud as crud

router = APIRouter(prefix="/internal", tags=["internal"])

# Простая аутентификация для внутреннего API
def verify_internal_token(token: str = None):
    """
    Упрощенная аутентификация для внутреннего API
    """
    INTERNAL_TOKENS = os.getenv("INTERNAL_TOKENS", "internal-secret-token").split(",")
    
    if not token or token not in INTERNAL_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid internal token")
    return True

@router.get("/health/detailed")
async def detailed_health_check(
    token: str = None,
    db: Session = Depends(get_db)
):
    """
    Подробная проверка здоровья системы для внутреннего мониторинга
    
    Особенности по сравнению с публичным API:
    1. Возвращает технические детали (использование памяти, диска и т.д.)
    2. Проверяет соединения со всеми зависимостями
    3. Возвращает метрики производительности
    4. Не ограничивается по rate limit
    """
    # Проверяем токен
    verify_internal_token(token)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "status": "checking",
        "components": {}
    }
    
    # 1. Проверка базы данных
    try:
        with engine.connect() as conn:
            # Проверяем основные таблицы
            author_count = conn.execute("SELECT COUNT(*) FROM authors").scalar()
            book_count = conn.execute("SELECT COUNT(*) FROM books").scalar()
            
            # Проверяем производительность
            start = datetime.now()
            conn.execute("SELECT 1")
            db_latency = (datetime.now() - start).total_seconds() * 1000
            
            result["components"]["database"] = {
                "status": "healthy",
                "latency_ms": round(db_latency, 2),
                "tables": {
                    "authors": author_count,
                    "books": book_count
                },
                "connection_pool": {
                    "checked_out": engine.pool.checkedout(),
                    "checked_in": engine.pool.checkedin(),
                    "size": engine.pool.size()
                }
            }
    except Exception as e:
        result["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        result["status"] = "degraded"
    
    # 2. Системные метрики
    try:
        # Использование памяти
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        result["components"]["system"] = {
            "status": "healthy",
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent
            },
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
    except Exception as e:
        result["components"]["system"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        result["status"] = "degraded"
    
    # 3. Статистика приложения
    try:
        # Статистика по последним операциям
        result["components"]["application"] = {
            "status": "healthy",
            "version": "2.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "start_time": "N/A" 
        }
    except Exception as e:
        result["components"]["application"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        result["status"] = "degraded"
    
    # Определяем общий статус
    all_healthy = all(
        comp.get("status") == "healthy" 
        for comp in result["components"].values()
    )
    result["status"] = "healthy" if all_healthy else "degraded"
    
    return result

@router.get("/metrics/usage")
async def usage_metrics(
    token: str = None,
    period_hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Метрики использования API для внутреннего анализа
    
    Особенности:
    1. Возвращает агрегированные данные об использовании
    2. Использует упрощенную логику (в реальном проекте можно использовать аналитическую БД)
    3. Не требует сложной аутентификации
    """
    # Проверяем токен
    verify_internal_token(token)
    
    # Пример упрощенной аналитики
    total_authors = db.query(models.Author).count()
    total_books = db.query(models.Book).count()
    
    # Книги по языкам
    books_by_language = db.query(
        models.Book.language,
        func.count(models.Book.id).label('count')
    ).group_by(models.Book.language).all()
    
    # Доступные книги
    available_books = db.query(models.Book).filter(models.Book.is_available == True).count()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "period_hours": period_hours,
        "summary": {
            "total_authors": total_authors,
            "total_books": total_books,
            "available_books": available_books,
            "availability_rate": round((available_books / total_books * 100) if total_books > 0 else 0, 2)
        },
        "breakdown": {
            "books_by_language": [
                {"language": lang, "count": count} 
                for lang, count in books_by_language
            ]
        },
        
    }


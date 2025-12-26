from fastapi import Request, HTTPException, status
from typing import Optional
import hashlib
import json
from datetime import datetime, timedelta
import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Используем Redis для хранения ключей идемпотентности
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

class IdempotencyKeyManager:
    @staticmethod
    def generate_key(request: Request, body: dict) -> str:
        """
        Генерирует ключ идемпотентности на основе запроса
        """
        path = request.url.path
        method = request.method
        client_id = request.client.host if request.client else "unknown"
        
        # Создаем хеш из пути, метода, клиента и тела запроса
        content = f"{path}:{method}:{client_id}:{json.dumps(body, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    @staticmethod
    def check_and_store(key: str, ttl_seconds: int = 3600) -> bool:
        """
        Проверяет существование ключа и сохраняет его
        Возвращает True если ключ уже существует (дубликат запроса)
        """
        if redis_client.exists(key):
            return True
        
        # Сохраняем ключ с TTL
        redis_client.setex(key, ttl_seconds, "processed")
        return False
    
    @staticmethod
    def get_response(key: str):
        """
        Получает сохраненный ответ для ключа идемпотентности
        """
        response_key = f"{key}:response"
        return redis_client.get(response_key)
    
    @staticmethod
    def store_response(key: str, response_data, ttl_seconds: int = 3600):
        """
        Сохраняет ответ для ключа идемпотентности
        Поддерживает SQLAlchemy модели, Pydantic модели и словари
        """
        response_key = f"{key}:response"
        
        # Преобразуем данные в словарь
        if hasattr(response_data, 'dict'):  # Pydantic модель
            data_dict = response_data.dict()
        elif hasattr(response_data, '__dict__'):  # SQLAlchemy модель или обычный объект
            data_dict = response_data.__dict__
            
            # Удаляем внутренние атрибуты SQLAlchemy
            if '_sa_instance_state' in data_dict:
                del data_dict['_sa_instance_state']
                
            # Преобразуем datetime в строки
            for k, v in data_dict.items():
                if isinstance(v, datetime):
                    data_dict[k] = v.isoformat()
        elif isinstance(response_data, dict):
            data_dict = response_data
        else:
            # Пробуем преобразовать любым способом
            try:
                data_dict = dict(response_data)
            except:
                data_dict = {"data": str(response_data)}
        
        redis_client.setex(response_key, ttl_seconds, json.dumps(data_dict))
        
        # Помечаем оригинальный ключ как завершенный
        redis_client.setex(key, ttl_seconds, "completed")
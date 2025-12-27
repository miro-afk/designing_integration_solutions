import hashlib
import json
import redis
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

class IdempotencyKeyManager:
    def __init__(self, prefix="idempotency:"):
        self.prefix = prefix
    
    def generate_key(self, action: str, data: dict, client_id: str = "unknown") -> str:
        """
        Генерирует ключ идемпотентности для сообщения
        """
        content = f"{action}:{client_id}:{json.dumps(data, sort_keys=True)}"
        return f"{self.prefix}{hashlib.sha256(content.encode()).hexdigest()}"
    
    def check_and_store(self, key: str, ttl_seconds: int = 3600) -> bool:
        """
        Проверяет существование ключа и сохраняет его
        Возвращает True если ключ уже существует (дубликат запроса)
        """
        full_key = f"{self.prefix}{key}"
        
        # Используем Redis транзакцию для атомарной проверки и установки
        pipe = redis_client.pipeline()
        pipe.exists(full_key)
        pipe.setex(full_key, ttl_seconds, "processing")
        results = pipe.execute()
        
        return results[0] == 1
    
    def get_response(self, key: str):
        """
        Получает сохраненный ответ для ключа идемпотентности
        """
        response_key = f"{self.prefix}{key}:response"
        result = redis_client.get(response_key)
        
        if result:
            try:
                return json.loads(result)
            except:
                return None
        return None
    
    def store_response(self, key: str, response_data, ttl_seconds: int = 3600):
        full_key = f"{self.prefix}{key}"
        response_key = f"{full_key}:response"
        
        # Функция для преобразования datetime
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        # Преобразуем данные
        if hasattr(response_data, 'dict'):
            data_dict = response_data.dict()
            # Преобразовать все datetime в dict
            data_dict = json.loads(json.dumps(data_dict, default=convert_datetime))
        elif hasattr(response_data, '__dict__'):
            data_dict = response_data.__dict__
            
            if '_sa_instance_state' in data_dict:
                del data_dict['_sa_instance_state']
                
            # Преобразуем datetime в строки
            for k, v in data_dict.items():
                if isinstance(v, datetime):
                    data_dict[k] = v.isoformat()
        elif isinstance(response_data, dict):
            data_dict = response_data
            # Обработать и вложенные dict
            data_dict = json.loads(json.dumps(data_dict, default=convert_datetime))
        else:
            data_dict = {"data": str(response_data)}
    
    # Сохраняем ответ
        redis_client.setex(response_key, ttl_seconds, json.dumps(data_dict))
        redis_client.setex(full_key, ttl_seconds, "completed")
    
    def cleanup_old_keys(self, older_than_hours: int = 24):
        """
        Очищает старые ключи идемпотентности
        """
        # В production используйте Redis SCAN для больших наборов данных
        pattern = f"{self.prefix}*"
        keys = redis_client.keys(pattern)
        
        deleted = 0
        for key in keys:
            ttl = redis_client.ttl(key)
            if ttl == -1 or ttl > older_than_hours * 3600:
                redis_client.delete(key)
                deleted += 1
        
        return deleted
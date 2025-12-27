import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USERNAME: str = "admin"
    RABBITMQ_PASSWORD: str = "admin123"
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # PostgreSQL
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "library_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    
    # API
    API_KEYS: List[str] = ["test-api-key", "production-key-123"]
    INTERNAL_TOKENS: List[str] = ["internal-secret-token"]
    
    # Idempotency
    IDEMPOTENCY_TTL: int = 3600  # 1 час
    
    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5  # секунды
    
    class Config:
        env_file = ".env"

settings = Settings()
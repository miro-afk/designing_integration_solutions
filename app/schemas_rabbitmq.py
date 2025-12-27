from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List,Union  
from datetime import datetime
import uuid

class RabbitMQMessage(BaseModel):
    """Базовая схема сообщения RabbitMQ"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None

class RequestMessage(RabbitMQMessage):
    """Схема запроса от клиента"""
    version: str = Field(..., description="Версия API: v1 или v2")
    action: str = Field(..., description="Действие: create_author, get_books и т.д.")
    data: Optional[Dict[str, Any]] = None
    auth: Optional[str] = Field(None, description="API ключ для аутентификации")
    idempotency_key: Optional[str] = Field(None, description="Ключ идемпотентности")
    fields: Optional[str] = Field(None, description="Опциональные поля для ответа")

class ResponseMessage(RabbitMQMessage):
    """Схема ответа от сервера"""
    status: str = Field(..., description="Статус: success, error, validation_error")
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    error: Optional[Dict[str, Any]] = None
    pagination: Optional[Dict[str, Any]] = None

class ErrorDetail(BaseModel):
    """Детали ошибки"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

# Специфичные схемы для различных действий
class AuthorData(BaseModel):
    name: str
    bio: Optional[str] = None
    birth_date: Optional[str] = None
    nationality: Optional[str] = None

class BookData(BaseModel):
    title: str
    isbn: str
    description: Optional[str] = None
    year_published: Optional[int] = None
    publisher: Optional[str] = None
    pages: Optional[int] = None
    language: str = "en"
    author_id: int
    is_available: Optional[bool] = True  # Только для v2

class PaginationParams(BaseModel):
    page: int = 1
    size: int = 100
    filters: Optional[Dict[str, Any]] = None
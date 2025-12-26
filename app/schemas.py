from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

# Common schemas
class TimestampMixin(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# V1 Schemas
class AuthorBaseV1(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    bio: Optional[str] = None
    birth_date: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=50)

class AuthorCreateV1(AuthorBaseV1):
    pass

class AuthorUpdateV1(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = None
    birth_date: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=50)

class AuthorV1(AuthorBaseV1, TimestampMixin):
    id: int
    books_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class BookBaseV1(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    isbn: str = Field(..., min_length=10, max_length=13, pattern=r'^[0-9\-]+$')
    description: Optional[str] = None
    year_published: Optional[int] = Field(None, ge=1000, le=datetime.now().year)
    publisher: Optional[str] = Field(None, max_length=100)
    pages: Optional[int] = Field(None, ge=1)
    language: str = Field("en", min_length=2, max_length=2)

class BookCreateV1(BookBaseV1):
    author_id: int

class BookUpdateV1(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    isbn: Optional[str] = Field(None, min_length=10, max_length=13, pattern=r'^[0-9\-]+$')
    description: Optional[str] = None
    year_published: Optional[int] = Field(None, ge=1000, le=datetime.now().year)
    publisher: Optional[str] = Field(None, max_length=100)
    pages: Optional[int] = Field(None, ge=1)
    language: Optional[str] = Field(None, min_length=2, max_length=2)
    author_id: Optional[int] = None

class BookV1(BookBaseV1, TimestampMixin):
    id: int
    author_id: int
    author: Optional[AuthorV1] = None
    
    class Config:
        from_attributes = True

# V2 Schemas (with additive changes)
class BookBaseV2(BookBaseV1):
    is_available: bool = True  # Новое поле для v2

class BookCreateV2(BookBaseV2):
    author_id: int

class BookUpdateV2(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    isbn: Optional[str] = Field(None, min_length=10, max_length=13, pattern=r'^[0-9\-]+$')
    description: Optional[str] = None
    year_published: Optional[int] = Field(None, ge=1000, le=datetime.now().year)
    publisher: Optional[str] = Field(None, max_length=100)
    pages: Optional[int] = Field(None, ge=1)
    language: Optional[str] = Field(None, min_length=2, max_length=2)
    author_id: Optional[int] = None
    is_available: Optional[bool] = None  # Новое поле

class BookV2(BookBaseV2, TimestampMixin):
    id: int
    author_id: int
    author: Optional[AuthorV1] = None
    
    class Config:
        from_attributes = True

# Response models
class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    size: int
    pages: int

class FieldSelector:
    @staticmethod
    def filter_response(data: dict, fields: str = None) -> dict:
        """
        Фильтрует ответ, оставляя только указанные поля
        
        Args:
            data: Словарь с данными
            fields: Строка с перечислением полей через запятую (например: "id,name,title")
        
        Returns:
            Отфильтрованный словарь
        """
        if not fields:
            return data
        
        # Разбиваем строку на отдельные поля
        requested_fields = [field.strip() for field in fields.split(',')]
        result = {}
        
        for field in requested_fields:
            if field in data:
                result[field] = data[field]
            # Поддержка вложенных полей (например: "author.name")
            elif '.' in field:
                parent_field, child_field = field.split('.', 1)
                if parent_field in data and isinstance(data[parent_field], dict):
                    if child_field in data[parent_field]:
                        if parent_field not in result:
                            result[parent_field] = {}
                        result[parent_field][child_field] = data[parent_field][child_field]
        
        return result

# Обновленная схема ответа с поддержкой опциональных полей
class FieldResponse(BaseModel):
    data: dict
    requested_fields: List[str] = []
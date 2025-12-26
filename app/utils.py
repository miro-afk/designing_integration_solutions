from typing import List
import app.models as models
import app.schemas as schemas
def sqlalchemy_to_dict(model_instance, exclude: List[str] = None) -> dict:
    """
    Преобразует SQLAlchemy объект в словарь
    """
    if not model_instance:
        return {}
    
    exclude = exclude or []
    result = {}
    
    # Получаем все атрибуты
    for key in dir(model_instance):
        # Пропускаем служебные атрибуты
        if key.startswith('_') or key in ['metadata', 'query', 'query_class']:
            continue
            
        value = getattr(model_instance, key)
        
        # Пропускаем методы и то, что в исключениях
        if callable(value) or key in exclude:
            continue
            
        result[key] = value
    
    return result

def author_to_pydantic(db_author: models.Author) -> schemas.AuthorV1:
    """
    Преобразует SQLAlchemy Author в Pydantic AuthorV1
    """
    if not db_author:
        return None
    
    author_data = {
        "id": db_author.id,
        "name": db_author.name,
        "bio": db_author.bio,
        "birth_date": db_author.birth_date,
        "nationality": db_author.nationality,
        "created_at": db_author.created_at,
        "updated_at": db_author.updated_at,
        "books_count": len(db_author.books) if hasattr(db_author, 'books') else 0
    }
    
    return schemas.AuthorV1(**author_data)

def book_to_pydantic_v1(db_book: models.Book) -> schemas.BookV1:
    """
    Преобразует SQLAlchemy Book в Pydantic BookV1
    """
    if not db_book:
        return None
    
    book_data = {
        "id": db_book.id,
        "title": db_book.title,
        "isbn": db_book.isbn,
        "description": db_book.description,
        "year_published": db_book.year_published,
        "publisher": db_book.publisher,
        "pages": db_book.pages,
        "language": db_book.language,
        "created_at": db_book.created_at,
        "updated_at": db_book.updated_at,
        "author_id": db_book.author_id,
        "is_available": db_book.is_available
    }
    
    # Добавляем автора, если он загружен
    if db_book.author and hasattr(db_book, 'author'):
        book_data["author"] = author_to_pydantic(db_book.author)
    
    return schemas.BookV1(**book_data)

def book_to_pydantic_v2(db_book: models.Book) -> schemas.BookV2:
    """
    Преобразует SQLAlchemy Book в Pydantic BookV2
    """
    if not db_book:
        return None
    
    book_data = {
        "id": db_book.id,
        "title": db_book.title,
        "isbn": db_book.isbn,
        "description": db_book.description,
        "year_published": db_book.year_published,
        "publisher": db_book.publisher,
        "pages": db_book.pages,
        "language": db_book.language,
        "created_at": db_book.created_at,
        "updated_at": db_book.updated_at,
        "author_id": db_book.author_id,
        "is_available": db_book.is_available
    }
    
    # Добавляем автора, если он загружен
    if db_book.author and hasattr(db_book, 'author'):
        book_data["author"] = author_to_pydantic(db_book.author)
    
    return schemas.BookV2(**book_data)
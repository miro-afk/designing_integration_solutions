from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Tuple, Union
import app.models as models
import app.schemas as schemas

# ====================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ======================



# ====================== AUTHOR CRUD ======================

def get_author(db: Session, author_id: int):
    """
    Получить автора по ID
    Возвращает Pydantic модель
    """
    db_author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not db_author:
        return None
    
    return db_author

def get_authors(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    name: Optional[str] = None
):
    """
    Получить список авторов с пагинацией
    Возвращает список Pydantic моделей и общее количество
    """
    query = db.query(models.Author)
    
    if name:
        query = query.filter(models.Author.name.ilike(f"%{name}%"))
    
    total = query.count()
    db_authors = query.offset(skip).limit(limit).all()
    
    
    
    return db_authors, total

def create_author(db: Session, author: schemas.AuthorCreateV1) -> schemas.AuthorV1:
    """
    Создать нового автора
    Возвращает Pydantic модель
    """
    db_author = models.Author(**author.dict())
    db.add(db_author)
    db.commit()
    db.refresh(db_author)
    
    return author_to_pydantic(db_author)

def update_author(
    db: Session, 
    author_id: int, 
    author_update: schemas.AuthorUpdateV1
):
    """
    Обновить информацию об авторе
    Возвращает Pydantic модель или None если не найден
    """
    db_author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not db_author:
        return None
    
    update_data = author_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_author, field, value)
    
    db.commit()
    db.refresh(db_author)
    
    return db_author

def delete_author(db: Session, author_id: int) -> bool:
    """
    Удалить автора
    Возвращает True если удалено, False если не найден
    """
    db_author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not db_author:
        return False
    
    db.delete(db_author)
    db.commit()
    return True

# ====================== BOOK CRUD ======================

def get_book(db: Session, book_id: int, load_author: bool = True):
    """
    Получить книгу по ID
    Возвращает Pydantic модель BookV1
    """
    query = db.query(models.Book)
    
    if load_author:
        query = query.options(joinedload(models.Book.author))
    
    db_book = query.filter(models.Book.id == book_id).first()
    if not db_book:
        return None
    
    return db_book

def get_book_v2(db: Session, book_id: int, load_author: bool = True):
    """
    Получить книгу по ID для API v2
    Возвращает Pydantic модель BookV2
    """
    query = db.query(models.Book)
    
    if load_author:
        query = query.options(joinedload(models.Book.author))
    
    db_book = query.filter(models.Book.id == book_id).first()
    if not db_book:
        return None
    
    return db_book

def get_books(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    title: Optional[str] = None, 
    author_id: Optional[int] = None,
    is_available: Optional[bool] = None,
    load_author: bool = True
):
    """
    Получить список книг с фильтрацией и пагинацией
    Возвращает список Pydantic моделей BookV1 и общее количество
    """
    query = db.query(models.Book)
    
    if load_author:
        query = query.options(joinedload(models.Book.author))
    
    if title:
        query = query.filter(models.Book.title.ilike(f"%{title}%"))
    if author_id:
        query = query.filter(models.Book.author_id == author_id)
    if is_available is not None:
        query = query.filter(models.Book.is_available == is_available)
    
    total = query.count()
    db_books = query.offset(skip).limit(limit).all()
  
    
    
    return db_books, total

def get_books_v2(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    title: Optional[str] = None, 
    author_id: Optional[int] = None,
    is_available: Optional[bool] = None,
    load_author: bool = True
):
    """
    Получить список книг для API v2
    Возвращает список Pydantic моделей BookV2 и общее количество
    """
    query = db.query(models.Book)
    
    if load_author:
        query = query.options(joinedload(models.Book.author))
    
    if title:
        query = query.filter(models.Book.title.ilike(f"%{title}%"))
    if author_id:
        query = query.filter(models.Book.author_id == author_id)
    if is_available is not None:
        query = query.filter(models.Book.is_available == is_available)
    
    total = query.count()
    db_books = query.offset(skip).limit(limit).all()
  
    
    return db_books, total

def create_book(db: Session, book: schemas.BookCreateV1):
    """
    Создать новую книгу (v1)
    Возвращает Pydantic модель BookV1
    """
    db_book = models.Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    
    # Загружаем автора для полного ответа
    db_book = db.query(models.Book).options(joinedload(models.Book.author)).filter(models.Book.id == db_book.id).first()
    
    return db_book

def create_book_v2(db: Session, book: schemas.BookCreateV2) -> schemas.BookV2:
    """
    Создать новую книгу (v2)
    Возвращает Pydantic модель BookV2
    """
    db_book = models.Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    
    # Загружаем автора для полного ответа
    db_book = db.query(models.Book).options(joinedload(models.Book.author)).filter(models.Book.id == db_book.id).first()
    
    return db_book

def update_book(
    db: Session, 
    book_id: int, 
    book_update: schemas.BookUpdateV1
):
    """
    Обновить информацию о книге (v1)
    Возвращает Pydantic модель BookV1
    """
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        return None
    
    update_data = book_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_book, field, value)
    
    db.commit()
    db.refresh(db_book)
    
    # Загружаем автора для полного ответа
    db_book = db.query(models.Book).options(joinedload(models.Book.author)).filter(models.Book.id == book_id).first()
    
    return db_book

def update_book_v2(
    db: Session, 
    book_id: int, 
    book_update: schemas.BookUpdateV2
):
    """
    Обновить информацию о книге (v2)
    Возвращает Pydantic модель BookV2
    """
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        return None
    
    update_data = book_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_book, field, value)
    
    db.commit()
    db.refresh(db_book)
    
    # Загружаем автора для полного ответа
    db_book = db.query(models.Book).options(joinedload(models.Book.author)).filter(models.Book.id == book_id).first()
    
    return db_book

def delete_book(db: Session, book_id: int) -> bool:
    """
    Удалить книгу
    Возвращает True если удалено, False если не найден
    """
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        return False
    
    db.delete(db_book)
    db.commit()
    return True